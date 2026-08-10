from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.viaje import Viaje
from app.services.saldo_service import saldo_service


class ViajeService:
    """Ciclo de vida del viaje, con la regla del saldo integrada:

    solicitar -> (conductor acepta) -> asignado -> en_curso -> completado
                                    \\-> rechazado (cuenta como rechazo del conductor)
    solicitado -> cancelado (si el cliente cancela, se devuelve la carrera)
    """

    @staticmethod
    def solicitar(db: Session, cliente_id: int, datos) -> Viaje:
        viaje = Viaje(
            cliente_id=cliente_id,
            origen_lat=datos.origen_lat,
            origen_lng=datos.origen_lng,
            destino_lat=datos.destino_lat,
            destino_lng=datos.destino_lng,
            origen_direccion=datos.origen_direccion,
            destino_direccion=datos.destino_direccion,
            tarifa=datos.tarifa,
            metodo_pago_cliente=datos.metodo_pago_cliente,
        )
        # Tarifa minima validada en el schema (ge=3.0) y aca de nuevo por defensa.
        if viaje.tarifa < settings.TARIFA_MINIMA_CARRERA:
            raise ValidationException(
                message=f"La tarifa minima por carrera es de {settings.TARIFA_MINIMA_CARRERA:.0f} soles"
            )
        db.add(viaje)
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def aceptar(db: Session, viaje_id: int, conductor_id: int) -> Viaje:
        """El conductor acepta: se consume 1 carrera de su saldo."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no esta disponible")

        saldo_service.consumir_carrera(db, conductor_id)

        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        viaje.conductor_id = conductor_id
        viaje.estado = "asignado"
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def rechazar(db: Session, viaje_id: int, conductor_id: int) -> Viaje:
        """El conductor rechaza: registra el rechazo (cada 3 -> -1 saldo) y
        el viaje vuelve a quedar 'solicitado' para otro conductor."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no esta disponible")

        saldo_service.registrar_rechazo(db, conductor_id)
        viaje.estado = "rechazado"
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def iniciar(db: Session, viaje_id: int) -> Viaje:
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "asignado":
            raise ValidationException(message="El viaje debe estar asignado para iniciar")
        viaje.estado = "en_curso"
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def completar(db: Session, viaje_id: int) -> Viaje:
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado not in ("asignado", "en_curso"):
            raise ValidationException(message="El viaje no se puede completar desde su estado actual")

        viaje.estado = "completado"
        conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
        if conductor:
            conductor.viajes_completados += 1
        cliente = db.query(Cliente).filter(Cliente.id == viaje.cliente_id).first()
        if cliente:
            cliente.viajes_realizados += 1

        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def cancelar(db: Session, viaje_id: int, quien: str) -> Viaje:
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado not in ("solicitado", "asignado", "en_curso"):
            raise ValidationException(message="Este viaje ya esta cerrado")

        # Regla del saldo: si el CLIENTE cancela, la carrera se devuelve.
        if quien == "cliente" and viaje.conductor_id is not None:
            saldo_service.devolver_carrera(db, viaje.conductor_id)
        elif quien == "conductor" and viaje.conductor_id is not None:
            # Cancelar una carrera YA aceptada cuenta como rechazo (regla del -1/3).
            saldo_service.registrar_rechazo(db, viaje.conductor_id)

        viaje.estado = "cancelado"
        viaje.cancelado_por = quien
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def historial_conductor(db: Session, conductor_id: int) -> list[Viaje]:
        return (
            db.query(Viaje)
            .filter(Viaje.conductor_id == conductor_id)
            .order_by(Viaje.created_at.desc())
            .limit(50)
            .all()
        )

    @staticmethod
    def historial_cliente(db: Session, cliente_id: int) -> list[Viaje]:
        return (
            db.query(Viaje)
            .filter(Viaje.cliente_id == cliente_id)
            .order_by(Viaje.created_at.desc())
            .limit(50)
            .all()
        )


viaje_service = ViajeService()
