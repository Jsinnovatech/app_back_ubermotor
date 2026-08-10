from datetime import date, datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.conductor import Conductor
from app.models.paquete_carrera import PaqueteCarrera
from app.models.recarga import Recarga


class SaldoService:
    """Regla de negocio del saldo de carreras (prepago diario):

    - El conductor COMPRA carreras por adelantado (recarga).
    - El saldo vale SOLO el dia de la recarga: no acumulable, al terminar
      el dia lo que no se uso se pierde (se trata como 0).
    - Aceptar una carrera: saldo -= 1.
    - Si el CLIENTE cancela: la carrera se devuelve al saldo.
    - Si el conductor RECHAZA 3 carreras: se descuenta 1 del saldo.
    - Con saldo 0, el conductor no puede aceptar mas carreras hasta recargar.
    """

    @staticmethod
    def _hoy() -> date:
        return datetime.now(timezone.utc).date()

    @staticmethod
    def saldo_actual(db: Session, conductor_id: int) -> int:
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor:
            raise NotFoundException(message="Conductor no encontrado")

        # Vigencia diaria: si el saldo es de otro dia, se trata como 0.
        if conductor.saldo_fecha is None or conductor.saldo_fecha.date() != SaldoService._hoy():
            return 0
        return conductor.saldo_carreras

    @staticmethod
    def acreditar_recarga(db: Session, conductor_id: int) -> None:
        """Acredita el saldo de las recargas pendientes del dia (estado -> acreditado)."""
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor:
            raise NotFoundException(message="Conductor no encontrado")

        hoy = SaldoService._hoy()
        pendientes = (
            db.query(Recarga)
            .filter(
                Recarga.conductor_id == conductor_id,
                Recarga.estado == "pendiente",
            )
            .all()
        )

        # Si ya hay saldo de HOY, se suma; si es de otro dia, se reinicia.
        if conductor.saldo_fecha is None or conductor.saldo_fecha.date() != hoy:
            conductor.saldo_carreras = 0
            conductor.saldo_fecha = datetime.now(timezone.utc)

        for recarga in pendientes:
            recarga.estado = "acreditado"
            conductor.saldo_carreras += recarga.carreras

        db.commit()

    @staticmethod
    def consumir_carrera(db: Session, conductor_id: int) -> None:
        """Al ACEPTAR una carrera: saldo -= 1. Bloquea si saldo == 0."""
        saldo = SaldoService.saldo_actual(db, conductor_id)
        if saldo <= 0:
            raise ValidationException(
                message="Sin saldo de carreras para hoy. Recarga un paquete para seguir aceptando carreras."
            )
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        conductor.saldo_carreras = saldo - 1
        db.commit()

    @staticmethod
    def devolver_carrera(db: Session, conductor_id: int) -> None:
        """Si el CLIENTE cancela: la carrera se devuelve al saldo (del dia de hoy)."""
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor or conductor.saldo_fecha is None:
            return
        if conductor.saldo_fecha.date() == SaldoService._hoy():
            conductor.saldo_carreras += 1
            db.commit()

    @staticmethod
    def registrar_rechazo(db: Session, conductor_id: int) -> None:
        """El conductor rechaza una carrera. Cada RECHAZOS_PARA_DESCUENTO (3)
        rechazos del dia, se descuenta 1 carrera del saldo y el contador se
        reinicia. El descuento nunca deja el saldo en negativo."""
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor:
            raise NotFoundException(message="Conductor no encontrado")

        hoy = SaldoService._hoy()
        if conductor.rechazos_fecha is None or conductor.rechazos_fecha.date() != hoy:
            conductor.rechazos_hoy = 0
            conductor.rechazos_fecha = datetime.now(timezone.utc)

        conductor.rechazos_hoy += 1
        if conductor.rechazos_hoy >= settings.RECHAZOS_PARA_DESCUENTO:
            if conductor.saldo_fecha is not None and conductor.saldo_fecha.date() == hoy:
                conductor.saldo_carreras = max(0, conductor.saldo_carreras - 1)
            conductor.rechazos_hoy = 0

        db.commit()

    @staticmethod
    def listar_paquetes(db: Session) -> list[PaqueteCarrera]:
        return (
            db.query(PaqueteCarrera)
            .filter(PaqueteCarrera.activo.is_(True))
            .order_by(PaqueteCarrera.monto.asc())
            .all()
        )

    @staticmethod
    def comprar_recarga(db: Session, conductor_id: int, paquete_id: int, metodo: str) -> Recarga:
        paquete = db.query(PaqueteCarrera).filter(PaqueteCarrera.id == paquete_id, PaqueteCarrera.activo.is_(True)).first()
        if not paquete:
            raise NotFoundException(message="Paquete no encontrado o desactivado")

        recarga = Recarga(
            conductor_id=conductor_id,
            paquete_id=paquete.id,
            monto=paquete.monto,
            carreras=paquete.carreras,
            metodo=metodo,
            estado="pendiente",
        )
        db.add(recarga)
        db.commit()
        db.refresh(recarga)
        return recarga


saldo_service = SaldoService()
