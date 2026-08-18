# Ciclo de vida de las ofertas de los conductores sobre un viaje 'solicitado'
# (patron InDrive). Regla central (Opcion A): el saldo se consume SOLO cuando el
# cliente Acepta la oferta; ofertar no descuenta nada.
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.conductor import Conductor
from app.models.vehiculo import Vehiculo
from app.models.viaje import Viaje
from app.models.viaje_oferta import ViajeOferta
from app.services.saldo_service import saldo_service

PLAZO_OFERTA_SEGUNDOS = 30
POR_PAGINA = 3


def _distancia_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    from math import asin, cos, radians, sin, sqrt

    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * asin(sqrt(a))


class ViajeOfertaService:
    @staticmethod
    def crear(db: Session, viaje_id: int, conductor_id: int, precio_ofertado: float) -> ViajeOferta:
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no acepta ofertas")

        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor or not conductor.aprobado:
            raise ValidationException(
                message="Tu cuenta esta en validacion. El administrador debe aprobarla para ofertar"
            )

        # Un conductor solo puede tener UNA carrera en curso; ofertar en varios
        # viajes 'solicitado' esta permitido (no consume saldo), pero si ya esta
        # asignado/en_curso en otro, no puede ofertar mas.
        tiene_activa = (
            db.query(Viaje)
            .filter(Viaje.conductor_id == conductor_id, Viaje.estado.in_(("asignado", "en_curso")))
            .first()
        )
        if tiene_activa:
            raise ValidationException(message="Ya tienes una carrera en curso, completa la actual para ofertar")

        # Deja de ofertar en el mismo viaje las ofertas previas activas del
        # conductor (re-oferta).
        db.query(ViajeOferta).filter(
            ViajeOferta.viaje_id == viaje_id,
            ViajeOferta.conductor_id == conductor_id,
            ViajeOferta.estado == "activa",
        ).update({"estado": "vencida"})

        oferta = ViajeOferta(
            viaje_id=viaje_id,
            conductor_id=conductor_id,
            precio_ofertado=round(precio_ofertado, 2),
            vence_en=datetime.now(timezone.utc) + timedelta(seconds=PLAZO_OFERTA_SEGUNDOS),
        )
        db.add(oferta)
        db.commit()
        db.refresh(oferta)
        return oferta

    @staticmethod
    def listar_para_cliente(db: Session, viaje_id: int, offset: int = 0) -> list[dict]:
        """Propuestas activas del viaje, paginadas de a 3. Marca como 'vencida'
        las que ya pasaron el plazo de 30s."""
        ahora = datetime.now(timezone.utc)
        db.query(ViajeOferta).filter(
            ViajeOferta.viaje_id == viaje_id,
            ViajeOferta.estado == "activa",
            ViajeOferta.vence_en.isnot(None),
            ViajeOferta.vence_en < ahora,
        ).update({"estado": "vencida"})
        db.commit()

        ofertas = (
            db.query(ViajeOferta)
            .filter(ViajeOferta.viaje_id == viaje_id, ViajeOferta.estado == "activa")
            .order_by(ViajeOferta.precio_ofertado.asc())
            .offset(offset)
            .limit(POR_PAGINA)
            .all()
        )
        return [ViajeOfertaService._oferta_con_conductor(db, o) for o in ofertas]

    @staticmethod
    def aceptar(db: Session, viaje_id: int, oferta_id: int, cliente_id: int) -> Viaje:
        """El cliente acepta la oferta: consume el saldo de ese conductor
        (Opcion A), asigna el conductor y cierra las demas ofertas."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.cliente_id != cliente_id:
            raise ValidationException(message="Este viaje no te pertenece")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no esta disponible")

        oferta = db.query(ViajeOferta).filter(ViajeOferta.id == oferta_id).first()
        if not oferta or oferta.viaje_id != viaje_id or oferta.estado != "activa":
            raise ValidationException(message="Esta oferta ya no esta disponible")

        # Opcion A: el saldo se consume al aceptar la oferta.
        saldo_service.consumir_carrera(db, oferta.conductor_id)

        viaje.conductor_id = oferta.conductor_id
        viaje.tarifa = oferta.precio_ofertado
        viaje.estado = "asignado"

        # Cierra todas las ofertas del viaje: la elegida queda 'aceptada', el
        # resto 'vencida' (el conductor perdedor no pierde saldo).
        ahora = datetime.now(timezone.utc)
        for o in db.query(ViajeOferta).filter(ViajeOferta.viaje_id == viaje_id).all():
            if o.id == oferta_id:
                o.estado = "aceptada"
                o.accepted_at = ahora
            else:
                o.estado = "vencida"

        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def retirar(db: Session, viaje_id: int, oferta_id: int, conductor_id: int) -> ViajeOferta:
        oferta = db.query(ViajeOferta).filter(ViajeOferta.id == oferta_id).first()
        if not oferta or oferta.viaje_id != viaje_id:
            raise NotFoundException(message="Oferta no encontrada")
        if oferta.conductor_id != conductor_id:
            raise ValidationException(message="Esta oferta no te pertenece")
        if oferta.estado != "activa":
            raise ValidationException(message="Esta oferta ya no esta activa")
        oferta.estado = "retirada"
        db.commit()
        db.refresh(oferta)
        return oferta

    @staticmethod
    def _oferta_con_conductor(db: Session, oferta: ViajeOferta) -> dict:
        conductor = db.query(Conductor).filter(Conductor.id == oferta.conductor_id).first()
        vehiculo = db.query(Vehiculo).filter(Vehiculo.conductor_id == oferta.conductor_id).first()
        viaje = db.query(Viaje).filter(Viaje.id == oferta.viaje_id).first()

        distancia = None
        if conductor and viaje and conductor.ubicacion_lat is not None and conductor.ubicacion_lng is not None:
            distancia = round(
                _distancia_km(
                    conductor.ubicacion_lat,
                    conductor.ubicacion_lng,
                    viaje.origen_lat,
                    viaje.origen_lng,
                ),
                2,
            )

        # ETA aproximada en ciudad: 25 km/h constantes.
        eta_min = int(distancia / 25 * 60) if distancia is not None else None

        return {
            "id": oferta.id,
            "viaje_id": oferta.viaje_id,
            "conductor_id": oferta.conductor_id,
            "precio_ofertado": oferta.precio_ofertado,
            "estado": oferta.estado,
            "conductor_nombre": conductor.nombre if conductor else None,
            "conductor_rating": conductor.rating_promedio if conductor else None,
            "conductor_foto_url": conductor.foto_url if conductor else None,
            "moto_descripcion": (vehiculo.marca + " " + vehiculo.modelo).strip()
            if vehiculo and vehiculo.marca
            else None,
            "moto_placa": vehiculo.placa if vehiculo else None,
            "distancia_km": distancia,
            "eta_minutos": eta_min,
        }


viaje_oferta_service = ViajeOfertaService()