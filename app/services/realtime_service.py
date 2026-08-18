# Conexiones WebSocket de los conductores en memoria. Cuando un cliente pide
# un viaje, el backend EMPUJA el viaje a los conductores conectados en <1s
# (patron real de ride-hailing, tipo InDrive) en vez de esperar el polling.
import asyncio
import logging
from typing import Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class RealtimeManager:
    def __init__(self):
        # conexiones de conductores (reciben carreras nuevas)
        self._conexiones: Dict[int, WebSocket] = {}
        # conexiones de clientes (reciben la ubicacion en vivo del conductor)
        self._clientes: Dict[int, WebSocket] = {}

    # ---------- Conductores ----------

    async def conectar_conductor(self, conductor_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        previa = self._conexiones.pop(conductor_id, None)
        if previa is not None:
            try:
                await previa.close()
            except Exception:
                pass
        self._conexiones[conductor_id] = websocket
        logger.info(f"Conductor {conductor_id} conectado al WS ({len(self._conexiones)} activos)")

    def desconectar_conductor(self, conductor_id: int) -> None:
        if self._conexiones.pop(conductor_id, None) is not None:
            logger.info(f"Conductor {conductor_id} desconectado del WS ({len(self._conexiones)} activos)")

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
            try:
                await previa.close()
            except Exception:
                pass
        self._clientes[cliente_id] = websocket
        logger.info(f"Cliente {cliente_id} conectado al WS ({len(self._clientes)} clientes)")

    def desconectar_cliente(self, cliente_id: int) -> None:
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
        viaje_llegado, etc). Clave por usuario_id (igual que conectar_cliente)."""
        ws = self._clientes.get(usuario_id)
        if ws is None:
            return False
        try:
            await ws.send_json(datos)
            return True
        except Exception:
            self.desconectar_cliente(usuario_id)
            return False


realtime_manager = RealtimeManager()
