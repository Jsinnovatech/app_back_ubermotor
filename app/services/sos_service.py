import logging

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.alerta_sos import AlertaSOS
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.models.vehiculo import Vehiculo
from app.models.viaje import Viaje

logger = logging.getLogger(__name__)


class SosService:
    """Alerta de emergencia: junta los datos del que pide ayuda + su
    contraparte (cliente/chofer) + moto y seguro, la guarda en la BD y
    dispara el webhook a Serenazgo/Policia."""

    @staticmethod
    def _perfil_conductor(db: Session, usuario_id: int) -> Conductor | None:
        return db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()

    @staticmethod
    def _perfil_cliente(db: Session, usuario_id: int) -> Cliente | None:
        return db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()

    @staticmethod
    def crear(db: Session, origen: str, usuario_id: int, lat: float, lng: float) -> AlertaSOS:
        """Registra el SOS con todos los datos del involucrado y su contraparte."""
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()

        nombre_origen = usuario.email if usuario else None
        telefono_origen = usuario.telefono if usuario else None
        email_origen = usuario.email if usuario else None
        foto_origen_url = None
        moto_descripcion = None
        moto_foto_url = None
        seguro_descripcion = None
        contraparte_nombre = None
        contraparte_telefono = None
        contraparte_foto_url = None
        contraparte_ubicacion_lat = None
        contraparte_ubicacion_lng = None
        viaje_id = None

        if origen == "conductor":
            conductor = SosService._perfil_conductor(db, usuario_id)
            if conductor:
                nombre_origen = conductor.nombre
                foto_origen_url = conductor.foto_url
                viaje = (
                    db.query(Viaje)
                    .filter(Viaje.conductor_id == conductor.id, Viaje.estado.in_(["asignado", "en_curso"]))
                    .order_by(Viaje.created_at.desc())
                    .first()
                )
                if viaje:
                    viaje_id = viaje.id
                    cliente = db.query(Cliente).filter(Cliente.id == viaje.cliente_id).first()
                    if cliente:
                        contraparte_nombre = cliente.nombre
                        contraparte_foto_url = cliente.foto_url
                        c_user = db.query(Usuario).filter(Usuario.id == cliente.usuario_id).first()
                        contraparte_telefono = c_user.telefono if c_user else None
                vehiculo = db.query(Vehiculo).filter(Vehiculo.conductor_id == conductor.id).first()
                if vehiculo:
                    moto_descripcion = f"{vehiculo.marca or ''} {vehiculo.modelo or ''} {vehiculo.placa or ''}".strip()
                    moto_foto_url = vehiculo.foto_url
                if conductor.seguro_aseguradora:
                    seguro_descripcion = f"{conductor.seguro_aseguradora} {conductor.seguro_poliza or ''}".strip()
        else:  # cliente
            cliente = SosService._perfil_cliente(db, usuario_id)
            if cliente:
                nombre_origen = cliente.nombre
                foto_origen_url = cliente.foto_url
                viaje = (
                    db.query(Viaje)
                    .filter(Viaje.cliente_id == cliente.id, Viaje.estado.in_(["asignado", "en_curso"]))
                    .order_by(Viaje.created_at.desc())
                    .first()
                )
                if viaje:
                    viaje_id = viaje.id
                    conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
                    if conductor:
                        contraparte_nombre = conductor.nombre
                        contraparte_foto_url = conductor.foto_url
                        contraparte_ubicacion_lat = conductor.ubicacion_lat
                        contraparte_ubicacion_lng = conductor.ubicacion_lng
                        c_user = db.query(Usuario).filter(Usuario.id == conductor.usuario_id).first()
                        contraparte_telefono = c_user.telefono if c_user else None
                        vehiculo = db.query(Vehiculo).filter(Vehiculo.conductor_id == conductor.id).first()
                        if vehiculo:
                            moto_descripcion = f"{vehiculo.marca or ''} {vehiculo.modelo or ''} {vehiculo.placa or ''}".strip()
                            moto_foto_url = vehiculo.foto_url

        alerta = AlertaSOS(
            origen=origen,
            usuario_id=usuario_id,
            viaje_id=viaje_id,
            nombre_origen=nombre_origen,
            telefono_origen=telefono_origen,
            email_origen=email_origen,
            foto_origen_url=foto_origen_url,
            moto_descripcion=moto_descripcion,
            moto_foto_url=moto_foto_url,
            seguro_descripcion=seguro_descripcion,
            ubicacion_lat=lat,
            ubicacion_lng=lng,
            contraparte_nombre=contraparte_nombre,
            contraparte_telefono=contraparte_telefono,
            contraparte_foto_url=contraparte_foto_url,
            contraparte_ubicacion_lat=contraparte_ubicacion_lat,
            contraparte_ubicacion_lng=contraparte_ubicacion_lng,
        )
        db.add(alerta)
        db.commit()
        db.refresh(alerta)

        SosService._enviar_webhook(alerta)
        return alerta

    @staticmethod
    def _enviar_webhook(alerta: AlertaSOS) -> None:
        """Notifica a Serenazgo/Policia. Si no hay endpoint configurado, la
        alerta queda igual registrada en la BD (los perfiles policia la ven)."""
        if not settings.POLICIA_WEBHOOK_URL:
            logger.warning(f"SOS #{alerta.id}: POLICIA_WEBHOOK_URL no configurado, solo queda en BD")
            return
        try:
            httpx.post(
                settings.POLICIA_WEBHOOK_URL,
                json={
                    "tipo": "alerta_sos",
                    "alerta_id": alerta.id,
                    "origen": alerta.origen,
                    "nombre": alerta.nombre_origen,
                    "telefono": alerta.telefono_origen,
                    "moto": alerta.moto_descripcion,
                    "seguro": alerta.seguro_descripcion,
                    "ubicacion": {"lat": alerta.ubicacion_lat, "lng": alerta.ubicacion_lng},
                    "contraparte": alerta.contraparte_nombre,
                    "fecha": alerta.created_at.isoformat(),
                },
                timeout=5.0,
            )
            logger.info(f"SOS #{alerta.id}: webhook enviado a {settings.POLICIA_WEBHOOK_URL}")
        except Exception as e:
            logger.error(f"SOS #{alerta.id}: fallo el webhook: {e}")

    @staticmethod
    def cerrar(db: Session, alerta_id: int) -> AlertaSOS:
        from app.core.exceptions import NotFoundException

        alerta = db.query(AlertaSOS).filter(AlertaSOS.id == alerta_id).first()
        if not alerta:
            raise NotFoundException(message="Alerta no encontrada")
        alerta.estado = "atendida"
        db.commit()
        db.refresh(alerta)
        return alerta

    @staticmethod
    def listar_alertas(db: Session, estado: str = "activa") -> list[AlertaSOS]:
        """Alertas SOS por estado (activa/atendida) para la Central de la policia."""
        return (
            db.query(AlertaSOS)
            .filter(AlertaSOS.estado == estado)
            .order_by(AlertaSOS.created_at.desc())
            .all()
        )

    @staticmethod
    def ubicacion_vivo_conductor(db: Session, alerta_id: int) -> dict:
        """Posicion ACTUAL del conductor de la alerta (para seguir la moto en
        movimiento en el mapa de la policia)."""
        from app.core.exceptions import NotFoundException

        alerta = db.query(AlertaSOS).filter(AlertaSOS.id == alerta_id).first()
        if not alerta or not alerta.viaje_id:
            raise NotFoundException(message="Alerta sin viaje activo")

        viaje = db.query(Viaje).filter(Viaje.id == alerta.viaje_id).first()
        if not viaje or not viaje.conductor_id:
            raise NotFoundException(message="Alerta sin conductor asignado")

        conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
        if not conductor or conductor.ubicacion_lat is None:
            raise NotFoundException(message="Conductor sin ubicacion registrada")

        return {
            "conductor_id": conductor.id,
            "lat": conductor.ubicacion_lat,
            "lng": conductor.ubicacion_lng,
        }


sos_service = SosService()
