# Notificaciones push via OneSignal: despiertan el telefono del conductor o
# cliente aunque la app este cerrada o en segundo plano (el WebSocket solo
# funciona con la app abierta, el push llega siempre).
#
# El front registra su dispositivo en OneSignal con un "external id" propio:
#   conductor_{usuario_id}  o  cliente_{usuario_id}
# y el backend apunta a esos ids. Un solo POST a la API de OneSignal reemplaza
# todo el trabajo de configurar Firebase/APNs a mano.
import asyncio
import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.services.viaje_service import conductores_disponibles_cerca

logger = logging.getLogger(__name__)

_ONESIGNAL_API = "https://api.onesignal.com/notifications"


def _ids_conductor(conductor_id: int) -> str:
    return f"conductor_{conductor_id}"


def _ids_cliente(cliente_id: int) -> str:
    return f"cliente_{cliente_id}"


class PushService:
    @property
    def _habilitado(self) -> bool:
        return bool(settings.ONESIGNAL_APP_ID and settings.ONESIGNAL_REST_API_KEY)

    async def enviar(
        self,
        external_ids: list[str],
        titulo: str,
        cuerpo: str,
        data: dict | None = None,
    ) -> bool:
        """Empuja una notificacion a uno o varios dispositivos por external id.
        Devuelve True si OneSignal acepto el envio (no es entrega garantizada)."""
        if not self._habilitado or not external_ids:
            return False
        payload = {
            "app_id": settings.ONESIGNAL_APP_ID,
            "include_external_user_ids": list(dict.fromkeys(external_ids)),
            "headings": {"en": titulo, "es": titulo},
            "contents": {"en": cuerpo, "es": cuerpo},
            "data": data or {},
            # Prioridad alta para que se muestre como notificacion destacada
            # (heads-up) en Android y suene/vibre aunque la app este cerrada.
            "priority": 10,
            "android_accent_color": "FFF5B800",
            "ios_badgeType": "None",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as cliente:
                resp = await cliente.post(
                    _ONESIGNAL_API,
                    headers={"Authorization": f"Basic {settings.ONESIGNAL_REST_API_KEY}"},
                    json=payload,
                )
            if resp.status_code not in (200, 201, 202):
                logger.warning("OneSignal rechazo el push (%s): %s", resp.status_code, resp.text[:300])
                return False
            return True
        except Exception as e:
            logger.warning("Fallo el push a OneSignal: %s", e)
            return False

    def lanzar(self, coro) -> None:
        """Dispara el push en background para no bloquear la respuesta HTTP."""
        try:
            asyncio.create_task(coro)
        except Exception as e:
            logger.warning("No se pudo lanzar el push en background: %s", e)

    # ---------- Eventos de negocio ----------

    def notificar_nueva_carrera(self, db: Session, lat: float, lng: float, viaje: dict) -> None:
        """Cliente pide carrera -> push a los conductores cerca (aprobados,
        disponibles, con saldo). Con la app cerrada el telefono suena igual."""
        if not self._habilitado:
            return
        cercanos = conductores_disponibles_cerca(db, lat, lng)
        if not cercanos:
            return
        ids = []
        for c in cercanos:
            conductor = db.query(Conductor).filter(Conductor.id == c["conductor_id"]).first()
            if conductor is not None:
                ids.append(_ids_conductor(conductor.usuario_id))
        self.lanzar(self.enviar(
            ids,
            "Nueva carrera disponible",
            f"Cliente en {viaje.get('origen_direccion') or 'origen'} · S/ {viaje.get('tarifa', 0):.2f}",
            {"tipo": "viaje_nuevo", "viaje_id": viaje.get("id")},
        ))

    def notificar_conductor_en_camino(self, db: Session, viaje: dict, cliente_id: int) -> None:
        """Conductor acepta -> push al cliente 'tu conductor esta en camino'."""
        if not self._habilitado:
            return
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente is None:
            return
        nombre = viaje.get("conductor_nombre") or "Tu conductor"
        moto = viaje.get("moto_descripcion") or ""
        placa = viaje.get("moto_placa") or ""
        detalle = " ".join(x for x in (moto, placa) if x).strip()
        cuerpo = f"{nombre} aceptó tu carrera. Está en camino." if not detalle else f"{nombre} ({detalle}) está en camino."
        self.lanzar(self.enviar(
            [_ids_cliente(cliente.usuario_id)],
            "🚴 Conductor en camino",
            cuerpo,
            {"tipo": "viaje_aceptado", "viaje_id": viaje.get("id")},
        ))

    def notificar_conductor_llego(self, db: Session, viaje: dict, cliente_id: int) -> None:
        if not self._habilitado:
            return
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente is None:
            return
        self.lanzar(self.enviar(
            [_ids_cliente(cliente.usuario_id)],
            "Tu conductor llegó",
            "Tu conductor ya está esperando en el punto de recogida.",
            {"tipo": "viaje_llegado", "viaje_id": viaje.get("id")},
        ))

    def notificar_viaje_completado(self, db: Session, viaje: dict, cliente_id: int) -> None:
        if not self._habilitado:
            return
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if cliente is None:
            return
        self.lanzar(self.enviar(
            [_ids_cliente(cliente.usuario_id)],
            "Viaje completado",
            f"Carrera finalizada. Gracias por viajar con HablaVas (S/ {viaje.get('tarifa', 0):.2f}).",
            {"tipo": "viaje_completado", "viaje_id": viaje.get("id")},
        ))

    def notificar_viaje_cancelado(self, db: Session, viaje: dict, conductor_id: int) -> None:
        """Al cliente cancela -> avisa al conductor que tenia la carrera."""
        if not self._habilitado or conductor_id is None:
            return
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if conductor is None:
            return
        self.lanzar(self.enviar(
            [_ids_conductor(conductor.usuario_id)],
            "Carrera cancelada",
            "El cliente canceló la carrera. La oferta vuelve a estar disponible.",
            {"tipo": "viaje_cancelado", "viaje_id": viaje.get("id")},
        ))


push_service = PushService()
