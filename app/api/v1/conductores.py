from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, get_usuario_actual, UsuarioActual
from app.core.exceptions import NotFoundException, ValidationException
from app.database import get_db
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.schemas.conductor import (
    ConductorIn,
    ConductorOut,
    DisponibilidadIn,
    SaldoOut,
    UbicacionIn,
    VehiculoIn,
)
from app.schemas.recarga import PaqueteOut, RecargaOut, ComprarRecargaIn
from app.schemas.viaje import ViajeOut
from app.services.saldo_service import saldo_service
from app.services.storage.imagekit_service import imagekit_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/conductores", tags=["🛵 Conductores"])


def _conductor_de_usuario(db: Session, usuario_id: int) -> Conductor:
    conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()
    if not conductor:
        raise NotFoundException(message="Perfil de conductor no encontrado")
    return conductor


@router.post("/documentos", response_model=ConductorOut)
async def subir_documento(
    tipo: str,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Sube un documento del conductor a ImageKit. tipo: foto | dni | licencia | antecedentes.
    El admin revisa los documentos y aprueba (aprobado)."""
    tipos_validos = {"foto", "dni", "licencia", "antecedentes"}
    if tipo not in tipos_validos:
        raise ValidationException(message=f"tipo debe ser uno de: {', '.join(sorted(tipos_validos))}")

    if not imagekit_service.disponible:
        raise ValidationException(message="Storage no configurado (falta IMAGEKIT_PRIVATE_KEY)")

    contenido = await archivo.read()
    if not contenido:
        raise ValidationException(message="Archivo vacio")

    resultado = imagekit_service.subir(
        file_content=contenido,
        file_name=archivo.filename or f"{tipo}.jpg",
        folder=f"hablavas/conductores/{usuario.usuario_id}",
    )
    if resultado is None:
        raise ValidationException(message="No se pudo subir el archivo")

    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    if tipo == "foto":
        conductor.foto_url = resultado.url
    elif tipo == "dni":
        conductor.dni_foto_url = resultado.url
    elif tipo == "licencia":
        conductor.licencia_foto_url = resultado.url
    elif tipo == "antecedentes":
        conductor.antecedentes_foto_url = resultado.url
        conductor.antecedentes_valido = None  # pendiente de revision del admin

    db.commit()
    db.refresh(conductor)
    conductor.saldo_carreras = saldo_service.saldo_actual(db, conductor.id)
    return conductor


@router.get("/perfil", response_model=ConductorOut)
async def mi_perfil(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Perfil del conductor. El saldo respeta la vigencia diaria (no acumulable):
    si saldo_fecha es de otro dia, se reporta 0."""
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.saldo_carreras = saldo_service.saldo_actual(db, conductor.id)
    return conductor


@router.put("/perfil", response_model=ConductorOut)
async def actualizar_perfil(
    datos: ConductorIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.nombre = datos.nombre
    if datos.dni is not None:
        conductor.dni = datos.dni
    if datos.licencia is not None:
        conductor.licencia = datos.licencia
    if datos.vehiculo is not None:
        v = datos.vehiculo
        vehiculo = conductor.vehiculo
        if vehiculo is None:
            from app.models.vehiculo import Vehiculo

            vehiculo = Vehiculo(conductor_id=conductor.id)
            db.add(vehiculo)
        vehiculo.marca = v.marca or vehiculo.marca
        vehiculo.modelo = v.modelo or vehiculo.modelo
        vehiculo.placa = v.placa or vehiculo.placa
        vehiculo.color = v.color or vehiculo.color
    db.commit()
    db.refresh(conductor)
    return conductor


@router.put("/disponibilidad", response_model=ConductorOut)
async def cambiar_disponibilidad(
    datos: DisponibilidadIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.disponible = datos.disponible
    db.commit()
    db.refresh(conductor)
    return conductor


@router.put("/ubicacion")
async def actualizar_ubicacion(
    datos: UbicacionIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.ubicacion_lat = datos.lat
    conductor.ubicacion_lng = datos.lng
    db.commit()
    return {"message": "Ubicacion actualizada"}


@router.get("/saldo", response_model=SaldoOut)
async def mi_saldo(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return {
        "conductor_id": conductor.id,
        "saldo_carreras": saldo_service.saldo_actual(db, conductor.id),
        "saldo_fecha": conductor.saldo_fecha.isoformat() if conductor.saldo_fecha else None,
    }


@router.get("/paquetes", response_model=list[PaqueteOut])
async def listar_paquetes(db: Session = Depends(get_db)):
    return saldo_service.listar_paquetes(db)


@router.post("/recargar", response_model=RecargaOut)
async def recargar(
    datos: ComprarRecargaIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Compra un paquete (2/4/8 soles). Queda 'pendiente' hasta confirmar el pago."""
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return saldo_service.comprar_recarga(db, conductor.id, datos.paquete_id, datos.metodo)


@router.get("/historial", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_conductor(db, conductor.id)
