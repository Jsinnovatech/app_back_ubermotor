# Conexiones WebSocket de los conductores en memoria. Cuando un cliente pide
# un viaje, el backend EMPUJA el viaje a los conductores conectados en <1s
# (patron real de ride-hailing, tipo InDrive) en vez de esperar el polling.
import asyncio
import logging
import time
from typing import Dict, Tuple

from fastapi import WebSocket

logger = logging.getLogger(__name__)

# Heartbeat: cada cuanto se manda un ping y cuanto se espera el pong antes de
# dar la conexion por muerta (zombie - el celular la mato en segundo plano
# sin avisar, el backend seguia creyendo que estaba conectada). Ver skill
# websocket-realtime-fastapi-flutter para el detalle de por que hace falta.
HEARTBEAT_INTERVAL = 25  # segundos entre pings
HEARTBEAT_TIMEOUT = 10  # gracia para recibir el pong


class RealtimeManager:
    def __init__(self):
        # conexiones de conductores (reciben carreras nuevas)
        self._conexiones: Dict[int, WebSocket] = {}
        # conexiones de clientes (reciben la ubicacion en vivo del conductor)
        self._clientes: Dict[int, WebSocket] = {}
        # Heartbeat: ultimo pong recibido y task de vigilancia por conexion.
        # Clave (tipo, id) para no mezclar un conductor_id con un cliente_id
        # que por coincidencia tengan el mismo numero.
        self._ultimo_pong: Dict[Tuple[str, int], float] = {}
        self._heartbeat_tasks: Dict[Tuple[str, int], asyncio.Task] = {}

    # ---------- Heartbeat (deteccion de conexiones zombie) ----------

    def registrar_pong(self, tipo: str, id_: int) -> None:
        """Se llama cuando llega un {"tipo": "pong"} del conductor/cliente."""
        self._ultimo_pong[(tipo, id_)] = time.monotonic()

    def _iniciar_heartbeat(self, tipo: str, id_: int, websocket: WebSocket, desconectar_fn) -> None:
        self._ultimo_pong[(tipo, id_)] = time.monotonic()
        anterior = self._heartbeat_tasks.pop((tipo, id_), None)
        if anterior is not None:
            anterior.cancel()
        self._heartbeat_tasks[(tipo, id_)] = asyncio.create_task(
            self._heartbeat_loop(tipo, id_, websocket, desconectar_fn)
        )

    def _detener_heartbeat(self, tipo: str, id_: int) -> None:
        task = self._heartbeat_tasks.pop((tipo, id_), None)
        if task is not None:
            task.cancel()
        self._ultimo_pong.pop((tipo, id_), None)

    async def _heartbeat_loop(self, tipo: str, id_: int, websocket: WebSocket, desconectar_fn) -> None:
        """Cada HEARTBEAT_INTERVAL manda un ping; si no llega el pong dentro
        de HEARTBEAT_TIMEOUT, la conexion se da por zombie y se limpia del
        registro sin esperar a que el proximo envio real falle."""
        try:
            while True:
                await asyncio.sleep(HEARTBEAT_INTERVAL)
                try:
                    await websocket.send_json({"tipo": "ping"})
                except Exception:
                    desconectar_fn(id_)
                    break
                await asyncio.sleep(HEARTBEAT_TIMEOUT)
                ultimo = self._ultimo_pong.get((tipo, id_), 0.0)
                if time.monotonic() - ultimo > HEARTBEAT_INTERVAL:
                    logger.info(f"Heartbeat timeout: {tipo} {id_} sin pong, cerrando conexion zombie")
                    try:
                        await websocket.close(code=4000, reason="heartbeat_timeout")
                    except Exception:
                        pass
                    desconectar_fn(id_)
                    break
        except asyncio.CancelledError:
            pass

    # ---------- Conductores ----------

    async def conectar_conductor(self, conductor_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        previa = self._conexiones.pop(conductor_id, None)
        if previa is not None:
            self._detener_heartbeat("conductor", conductor_id)
            try:
                await previa.close()
            except Exception:
                pass
        self._conexiones[conductor_id] = websocket
        self._iniciar_heartbeat("conductor", conductor_id, websocket, self.desconectar_conductor)
        logger.info(f"Conductor {conductor_id} conectado al WS ({len(self._conexiones)} activos)")

    def desconectar_conductor(self, conductor_id: int) -> None:
        self._detener_heartbeat("conductor", conductor_id)
        if self._conexiones.pop(conductor_id, None) is not None:
            logger.info(f"Conductor {conductor_id} desconectado del WS ({len(self._conexiones)} activos)")

    async def enviar_a_conductor(self, conductor_usuario_id: int, datos: dict) -> bool:
        """Empuja un evento al conductor conectado (viaje_aceptado, etc).
        Clave por usuario_id (igual que conectar_conductor)."""
        ws = self._conexiones.get(conductor_usuario_id)
        if ws is None:
            return False
        try:
            await ws.send_json(datos)
            return True
        except Exception:
            self.desconectar_conductor(conductor_usuario_id)
            return False

    async def notificar_viaje(self, viaje: dict) -> int:
        """Empuja el viaje a todos los conductores conectados. Devuelve cuantos recibieron."""
        enviados = 0
        caidos = []
        for conductor_id, ws in list(self._conexiones.items()):
            try:
                await ws.send_json(viaje)
                enviados += 1
            except Exception:
                caidos.append(conductor_id)
        for conductor_id in caidos:
            self.desconectar_conductor(conductor_id)
        return enviados

    # ---------- Clientes (tracking en vivo) ----------

    async def conectar_cliente(self, cliente_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        previa = self._clientes.pop(cliente_id, None)
        if previa is not None:
            self._detener_heartbeat("cliente", cliente_id)
            try:
                await previa.close()
            except Exception:
                pass
        self._clientes[cliente_id] = websocket
        self._iniciar_heartbeat("cliente", cliente_id, websocket, self.desconectar_cliente)
        logger.info(f"Cliente {cliente_id} conectado al WS ({len(self._clientes)} clientes)")

    def desconectar_cliente(self, cliente_id: int) -> None:
        self._detener_heartbeat("cliente", cliente_id)
        if self._clientes.pop(cliente_id, None) is not None:
            logger.info(f"Cliente {cliente_id} desconectado del WS ({len(self._clientes)} clientes)")

    async def enviar_ubicacion_a_cliente(self, cliente_id: int, datos: dict) -> bool:
        """Empuja la ubicacion del conductor al cliente de ese viaje (tracking)."""
        ws = self._clientes.get(cliente_id)
        if ws is None:
            return False
        try:
            await ws.send_json(datos)
            return True
        except Exception:
            self.desconectar_cliente(cliente_id)
            return False

    async def enviar_a_cliente(self, usuario_id: int, datos: dict) -> bool:
        """Empuja un evento arbitrario al cliente conectado (viaje_aceptado,
        viaje_llegado, viaje_completado, etc). Clave por usuario_id (igual
        que conectar_cliente)."""
        ws = self._clientes.get(usuario_id)
        if ws is None:
            return False
        try:
            await ws.send_json(datos)
            return True
        except Exception:
            self.desconectar_cliente(usuario_id)
            return False

    async def notificar_a_todos_los_clientes(self, datos: dict) -> int:
        """Empuja un evento a TODOS los clientes conectados (ej: cambio de
        disponibilidad de un conductor). El cliente reacciona re-consultando
        las motos cercanas a su ubicacion. Devuelve cuantos recibieron."""
        enviados = 0
        caidos = []
        for usuario_id, ws in list(self._clientes.items()):
            try:
                await ws.send_json(datos)
                enviados += 1
            except Exception:
                caidos.append(usuario_id)
        for usuario_id in caidos:
            self.desconectar_cliente(usuario_id)
        return enviados


realtime_manager = RealtimeManager()
