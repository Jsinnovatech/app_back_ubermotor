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
        self._conexiones: Dict[int, WebSocket] = {}

    async def conectar(self, conductor_id: int, websocket: WebSocket) -> None:
        await websocket.accept()
        # Si el mismo conductor reconecta, cierra la vieja.
        previa = self._conexiones.pop(conductor_id, None)
        if previa is not None:
            try:
                await previa.close()
            except Exception:
                pass
        self._conexiones[conductor_id] = websocket
        logger.info(f"Conductor {conductor_id} conectado al WS ({len(self._conexiones)} activos)")

    def desconectar(self, conductor_id: int) -> None:
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
            self.desconectar(conductor_id)
        return enviados


realtime_manager = RealtimeManager()
