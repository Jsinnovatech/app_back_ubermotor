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
    def cliente_de_usuario(db: Session, usuario_id: int) -> Cliente:
        """Resuelve el perfil de cliente de un usuario autenticado."""
        cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()
        if not cliente:
            raise NotFoundException(message="Perfil de cliente no encontrado")
        return cliente

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
        """El conductor acepta: se consume 1 carrera de su saldo. Un conductor
        solo puede tener UNA carrera activa (asignada o en curso) a la vez."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado != "solicitado":
            raise ValidationException(message="Este viaje ya no esta disponible")

        tiene_activa = (
            db.query(Viaje)
            .filter(
                Viaje.conductor_id == conductor_id,
                Viaje.estado.in_(("asignado", "en_curso")),
            )
            .first()
        )
        if tiene_activa:
            raise ValidationException(
                message="Ya tienes una carrera en curso, completa la actual para aceptar otra"
            )

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
    def llegar(db: Session, viaje_id: int, conductor_id: int) -> Viaje:
        """El conductor puso 'Llegue': el viaje pasa a estado 'llegado' y el
        cliente ve que su conductor ya esta esperando en el punto de recogida."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.conductor_id != conductor_id:
            raise ValidationException(message="Este viaje no te pertenece")
        if viaje.estado != "asignado":
            raise ValidationException(message="El viaje debe estar asignado para registrar la llegada")
        viaje.estado = "llegado"
        db.commit()
        db.refresh(viaje)
        return viaje

    @staticmethod
    def iniciar(db: Session, viaje_id: int) -> Viaje:
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        if viaje.estado not in ("asignado", "llegado"):
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
    ) -> list[dict]:
        """Viajes 'solicitado' con info del rider (nombre + rating). Si el
        conductor manda su posicion, se filtran por cercania del ORIGEN."""
        q = db.query(Viaje).filter(Viaje.estado == "solicitado").order_by(Viaje.created_at.desc())

        if lat is None or lng is None:
            candidatos = q.limit(50).all()
        else:
            todos = q.limit(200).all()
            candidatos = [v for v in todos if _distancia_km(lat, lng, v.origen_lat, v.origen_lng) <= radio_km]

        return [ViajeService._viaje_con_rider(db, v) for v in candidatos]

    @staticmethod
    def serializar_para_push(db: Session, viaje: Viaje) -> dict:
        """Payload del push por WebSocket a los conductores: el viaje completo
        con rider (id, origen, destino, tarifa). El router no debe tocar los
        serializadores privados."""
        payload = ViajeService._viaje_con_rider(db, viaje)
        payload["tipo"] = "viaje_nuevo"
        return payload

    @staticmethod
    def _viaje_con_rider(db: Session, viaje: Viaje) -> dict:
        """Serie el viaje incluyendo el nombre y la puntuacion del rider."""
        cliente = db.query(Cliente).filter(Cliente.id == viaje.cliente_id).first()
        return {
            "id": viaje.id,
            "cliente_id": viaje.cliente_id,
            "conductor_id": viaje.conductor_id,
            "estado": viaje.estado,
            "origen_lat": viaje.origen_lat,
            "origen_lng": viaje.origen_lng,
            "destino_lat": viaje.destino_lat,
            "destino_lng": viaje.destino_lng,
            "origen_direccion": viaje.origen_direccion,
            "destino_direccion": viaje.destino_direccion,
            "tarifa": viaje.tarifa,
            "metodo_pago_cliente": viaje.metodo_pago_cliente,
            "rider_nombre": cliente.nombre if cliente else None,
            "rider_rating": cliente.rating_promedio if cliente else None,
            "rider_foto_url": cliente.foto_url if cliente else None,
        }

    @staticmethod
    def detalle(db: Session, viaje_id: int) -> dict:
        """Estado actual de un viaje con la info del rider."""
        viaje = db.query(Viaje).filter(Viaje.id == viaje_id).first()
        if not viaje:
            raise NotFoundException(message="Viaje no encontrado")
        return ViajeService._viaje_con_rider(db, viaje)

    @staticmethod
    def viaje_activo_de_conductor(db: Session, conductor_id: int) -> dict | None:
        """Devuelve el viaje activo del conductor (asignado/llegado/en_curso)
        con la info del rider, o None si no tiene ninguno."""
        viaje = (
            db.query(Viaje)
            .filter(Viaje.conductor_id == conductor_id, Viaje.estado.in_(("asignado", "llegado", "en_curso")))
            .order_by(Viaje.created_at.desc())
            .first()
        )
        if viaje is None:
            return None
        return ViajeService._viaje_con_rider(db, viaje)

    @staticmethod
    def historial_conductor(db: Session, conductor_id: int) -> list[dict]:
        """Viajes del conductor, con info del rider (nombre + rating + foto)
        para mostrar en la tarjeta del historial (Rides)."""
        viajes = (
            db.query(Viaje)
            .filter(Viaje.conductor_id == conductor_id)
            .order_by(Viaje.created_at.desc())
            .limit(50)
            .all()
        )
        return [ViajeService._viaje_con_rider(db, v) for v in viajes]

    @staticmethod
    def viaje_activo_de_cliente(db: Session, cliente_id: int) -> dict | None:
        """Devuelve el viaje en curso del cliente con los datos del conductor
        (nombre, moto, rating, foto) para la pantalla de seguimiento."""
        viaje = (
            db.query(Viaje)
            .filter(Viaje.cliente_id == cliente_id, Viaje.estado.in_(("asignado", "llegado", "en_curso")))
            .order_by(Viaje.created_at.desc())
            .first()
        )
        if viaje is None:
            return None
        return ViajeService._viaje_con_conductor(db, viaje)

    @staticmethod
    def _viaje_con_conductor(db: Session, viaje: Viaje) -> dict:
        """Serie el viaje incluyendo los datos del conductor que el cliente ve
        en la pantalla de seguimiento (quien lo esta llevando)."""
        conductor = None
        vehiculo = None
        if viaje.conductor_id is not None:
            conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
            vehiculo = db.query(Vehiculo).filter(Vehiculo.conductor_id == conductor.id).first() if conductor else None

        base = ViajeService._viaje_con_rider(db, viaje)
        base.update(
            {
                "conductor_nombre": conductor.nombre if conductor else None,
                "conductor_rating": conductor.rating_promedio if conductor else None,
                "conductor_foto_url": conductor.foto_url if conductor else None,
                "moto_descripcion": (vehiculo.marca + " " + vehiculo.modelo).strip()
                if vehiculo and vehiculo.marca
                else None,
                "moto_placa": vehiculo.placa if vehiculo else None,
                "moto_foto_url": vehiculo.foto_url if vehiculo else None,
            }
        )
        return base

    @staticmethod
    def historial_cliente(db: Session, cliente_id: int) -> list[Viaje]:
        return (
            db.query(Viaje)
            .filter(Viaje.cliente_id == cliente_id)
            .order_by(Viaje.created_at.desc())
            .limit(50)
            .all()
        )

    @staticmethod
    def subir_foto_cliente(db: Session, cliente_id: int, url: str) -> Cliente:
        """Guarda la URL de la foto de perfil del cliente (la policia la ve en
        la Central SOS)."""
        cliente = db.query(Cliente).filter(Cliente.id == cliente_id).first()
        if not cliente:
            raise NotFoundException(message="Perfil de cliente no encontrado")
        cliente.foto_url = url
        db.commit()
        return cliente


viaje_service = ViajeService()
