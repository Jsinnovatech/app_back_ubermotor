from datetime import datetime, timezone

from fastapi import UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException, ValidationException
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.vehiculo import Vehiculo
from app.models.viaje import Viaje
from app.schemas.conductor import ConductorIn
from app.services.realtime_service import realtime_manager
from app.services.saldo_service import saldo_service
from app.services.storage.imagekit_service import imagekit_service

TIPOS_DOCUMENTO = {"foto", "dni", "licencia", "antecedentes", "moto"}


class ConductorService:
    """Regla de negocio del conductor: documentos, perfil, ubicacion y tracking."""

    @staticmethod
    def conductor_de_usuario(db: Session, usuario_id: int) -> Conductor:
        conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()
        if not conductor:
            raise NotFoundException(message="Perfil de conductor no encontrado")
        return conductor

    @staticmethod
    def perfil_con_saldo(db: Session, usuario_id: int) -> Conductor:
        """Perfil del conductor con el saldo vigente del dia (no acumulable) y
        el ingreso acumulado (suma de tarifas) de los viajes completados hoy."""
        conductor = ConductorService.conductor_de_usuario(db, usuario_id)
        conductor.saldo_carreras = saldo_service.saldo_actual(db, conductor.id)
        conductor.ingreso_hoy = ConductorService._ingreso_de_hoy(db, conductor.id)
        return conductor

    @staticmethod
    def _ingreso_de_hoy(db: Session, conductor_id: int) -> float:
        """Suma las tarifas de los viajes completados HOY por el conductor."""
        inicio = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
        total = (
            db.query(func.coalesce(func.sum(Viaje.tarifa), 0.0))
            .filter(
                Viaje.conductor_id == conductor_id,
                Viaje.estado == "completado",
                Viaje.created_at >= inicio,
            )
            .scalar()
        )
        return float(total or 0.0)

    @staticmethod
    async def subir_documento(db: Session, usuario_id: int, tipo: str, archivo: UploadFile) -> Conductor:
        """Sube un documento del conductor a ImageKit. tipo: foto | dni | licencia |
        antecedentes | moto. El admin revisa y aprueba (aprobado)."""
        if tipo not in TIPOS_DOCUMENTO:
            raise ValidationException(
                message=f"tipo debe ser uno de: {', '.join(sorted(TIPOS_DOCUMENTO))}"
            )

        if not imagekit_service.disponible:
            raise ValidationException(message="Storage no configurado (falta IMAGEKIT_PRIVATE_KEY)")

        contenido = await archivo.read()
        if not contenido:
            raise ValidationException(message="Archivo vacio")

        resultado = imagekit_service.subir(
            file_content=contenido,
            file_name=archivo.filename or f"{tipo}.jpg",
            folder=f"hablavas/conductores/{usuario_id}",
        )
        if resultado is None:
            raise ValidationException(message="No se pudo subir el archivo")

        conductor = ConductorService.conductor_de_usuario(db, usuario_id)
        if tipo == "foto":
            conductor.foto_url = resultado.url
        elif tipo == "dni":
            conductor.dni_foto_url = resultado.url
        elif tipo == "licencia":
            conductor.licencia_foto_url = resultado.url
        elif tipo == "antecedentes":
            conductor.antecedentes_foto_url = resultado.url
            conductor.antecedentes_valido = None  # pendiente de revision del admin
        elif tipo == "moto":
            vehiculo = conductor.vehiculo
            if vehiculo is None:
                vehiculo = Vehiculo(conductor_id=conductor.id)
                db.add(vehiculo)
            vehiculo.foto_url = resultado.url

        db.commit()
        db.refresh(conductor)
        conductor.saldo_carreras = saldo_service.saldo_actual(db, conductor.id)
        return conductor

    @staticmethod
    def actualizar_perfil(db: Session, usuario_id: int, datos: ConductorIn) -> Conductor:
        """Actualiza datos del conductor y su vehiculo (crea el vehiculo si no
        existe, sin pisar campos que el conductor no envio)."""
        conductor = ConductorService.conductor_de_usuario(db, usuario_id)
        conductor.nombre = datos.nombre
        if datos.dni is not None:
            conductor.dni = datos.dni
        if datos.licencia is not None:
            conductor.licencia = datos.licencia
        if datos.vehiculo is not None:
            v = datos.vehiculo
            vehiculo = conductor.vehiculo
            if vehiculo is None:
                vehiculo = Vehiculo(conductor_id=conductor.id)
                db.add(vehiculo)
            vehiculo.marca = v.marca or vehiculo.marca
            vehiculo.modelo = v.modelo or vehiculo.modelo
            vehiculo.placa = v.placa or vehiculo.placa
            vehiculo.color = v.color or vehiculo.color
        db.commit()
        db.refresh(conductor)
        return conductor

    @staticmethod
    def cambiar_disponibilidad(db: Session, usuario_id: int, disponible: bool) -> Conductor:
        conductor = ConductorService.conductor_de_usuario(db, usuario_id)
        conductor.disponible = disponible
        db.commit()
        db.refresh(conductor)
        return conductor

    @staticmethod
    async def actualizar_ubicacion(db: Session, usuario_id: int, lat: float, lng: float) -> None:
        """Guarda la posicion del conductor y, si tiene un viaje activo, empuja
        su ubicacion al cliente conectado por WebSocket (pin se mueve en vivo)."""
        conductor = ConductorService.conductor_de_usuario(db, usuario_id)
        conductor.ubicacion_lat = lat
        conductor.ubicacion_lng = lng
        db.commit()

        viaje_activo = (
            db.query(Viaje)
            .filter(Viaje.conductor_id == conductor.id, Viaje.estado.in_(["asignado", "llegado", "en_curso"]))
            .order_by(Viaje.created_at.desc())
            .first()
        )
        if viaje_activo:
            cliente = db.query(Cliente).filter(Cliente.id == viaje_activo.cliente_id).first()
            if cliente:
                await realtime_manager.enviar_ubicacion_a_cliente(
                    cliente.usuario_id,
                    {
                        "tipo": "ubicacion_conductor",
                        "viaje_id": viaje_activo.id,
                        "conductor_id": conductor.id,
                        "lat": lat,
                        "lng": lng,
                    },
                )


conductor_service = ConductorService()
