from math import asin, cos, radians, sin, sqrt

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import NotFoundException, ValidationException
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.viaje import Viaje
from app.models.vehiculo import Vehiculo
from app.services.saldo_service import saldo_service


def _distancia_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia Haversine en km entre dos coordenadas."""
    R = 6371.0
    dlat = radians(lat2 - lat1)
    dlng = radians(lng2 - lng1)
    a = sin(dlat / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlng / 2) ** 2
    return R * 2 * asin(sqrt(a))


def conductores_disponibles_cerca(
    db: Session,
    lat: float,
    lng: float,
    radio_km: float = 5.0,
) -> list[dict]:
    """Conductores activos, aprobados, disponibles y CON SALDO, ordenados por
    cercania. El cliente ve su ubicacion, moto y reputacion."""
    conductores = (
        db.query(Conductor)
        .filter(
            Conductor.aprobado.is_(True),
            Conductor.disponible.is_(True),
        )
        .all()
    )

    resultado = []
    for c in conductores:
        if c.ubicacion_lat is None or c.ubicacion_lng is None:
            continue
        if saldo_service.saldo_actual(db, c.id) <= 0:
            continue  # sin saldo no puede aceptar carreras hoy
        d = _distancia_km(lat, lng, c.ubicacion_lat, c.ubicacion_lng)
        if d > radio_km:
            continue
        vehiculo = db.query(Vehiculo).filter(Vehiculo.conductor_id == c.id).first()
        resultado.append({
            "conductor_id": c.id,
            "nombre": c.nombre,
            "foto_url": c.foto_url,
            "rating_promedio": c.rating_promedio,
            "viajes_completados": c.viajes_completados,
            "ubicacion_lat": c.ubicacion_lat,
            "ubicacion_lng": c.ubicacion_lng,
            "distancia_km": round(d, 2),
            "moto": {
                "marca": vehiculo.marca if vehiculo else None,
                "modelo": vehiculo.modelo if vehiculo else None,
                "placa": vehiculo.placa if vehiculo else None,
                "color": vehiculo.color if vehiculo else None,
                "foto_url": vehiculo.foto_url if vehiculo else None,
            },
        })

    resultado.sort(key=lambda x: x["distancia_km"])
    return resultado


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
        el viaje vuelve a quedar 'solicitado' para que otro conductor lo tome."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no esta disponible")

        saldo_service.registrar_rechazo(db, conductor_id)
        # Vuelve a 'solicitado' (sin conductor): la carrera sigue para otros.
        viaje.conductor_id = None
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
    def disponibles_cerca(
        db: Session,
        lat: float | None = None,
        lng: float | None = None,
        radio_km: float = 5.0,
    ) -> list[Viaje]:
        """Viajes 'solicitado'. Si el conductor manda su posicion, se filtran
        por cercania del ORIGEN (Haversine) dentro del radio -> solo su zona."""
        q = db.query(Viaje).filter(Viaje.estado == "solicitado").order_by(Viaje.created_at.desc())

        if lat is None or lng is None:
            return q.limit(50).all()

        candidatos = q.limit(200).all()
        return [v for v in candidatos if _distancia_km(lat, lng, v.origen_lat, v.origen_lng) <= radio_km]

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
