from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.calificacion import Calificacion
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.models.viaje import Viaje


class CalificacionService:
    """Calificacion 1-5 del viaje (cliente -> conductor, o al reves) y
    recalculo del rating_promedio del conductor (el ranking)."""

    @staticmethod
    def calificar(
        db: Session,
        viaje_id: int,
        autor_id: int,
        puntaje: int,
        comentario: str | None = None,
    ) -> Calificacion:
        if not (1 <= puntaje <= 5):
            raise ValidationException(message="El puntaje debe ser entre 1 y 5")

        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "completado":
            raise ValidationException(message="Solo se puede calificar un viaje completado")

        # Solo el cliente o el conductor del viaje pueden calificar.
        autor = db.query(Usuario).filter(Usuario.id == autor_id).first()
        es_cliente = db.query(Cliente).filter(Cliente.usuario_id == autor_id, Cliente.id == viaje.cliente_id).first()
        conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
        es_conductor = conductor is not None and conductor.usuario_id == autor_id
        if not (es_cliente or es_conductor):
            raise ValidationException(message="Solo el cliente o el conductor de este viaje pueden calificar")

        ya = db.query(Calificacion).filter(Calificacion.viaje_id == viaje_id).first()
        if ya:
            raise ValidationException(message="Este viaje ya fue calificado")

        cal = Calificacion(viaje_id=viaje_id, autor_id=autor_id, puntaje=puntaje, comentario=comentario)
        db.add(cal)

        # Si el que califico es el cliente, el puntaje va al conductor (ranking).
        if es_cliente and conductor:
            CalificacionService._recalcular_rating(db, conductor.id)

        db.commit()
        db.refresh(cal)
        return cal

    @staticmethod
    def _recalcular_rating(db: Session, conductor_id: int) -> None:
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor:
            return
        promedio = (
            db.query(func.avg(Calificacion.puntaje))
            .join(Viaje, Calificacion.viaje_id == Viaje.id)
            .filter(Viaje.conductor_id == conductor_id)
            .scalar()
        )
        if promedio is not None:
            conductor.rating_promedio = round(float(promedio), 1)

    @staticmethod
    def ranking(db: Session, top: int = 20) -> list[dict]:
        """Ranking de conductores por rating (desempate por viajes completados)."""
        conductores = (
            db.query(Conductor)
            .filter(Conductor.aprobado.is_(True))
            .order_by(Conductor.rating_promedio.desc(), Conductor.viajes_completados.desc())
            .limit(top)
            .all()
        )
        return [
            {
                "conductor_id": c.id,
                "nombre": c.nombre,
                "rating_promedio": c.rating_promedio,
                "viajes_completados": c.viajes_completados,
                "foto_url": c.foto_url,
            }
            for c in conductores
        ]


calificacion_service = CalificacionService()
