from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.core.exceptions import AuthorizationException, ValidationException
from app.database import get_db
from app.models.administrador import Administrador
from app.schemas.conductor import ConductorOut
from app.schemas.paquete import PaqueteCreate, PaqueteUpdate
from app.schemas.recarga import PaqueteOut, RecargaOut
from app.schemas.viaje import ViajeOut
from app.services.admin_service import admin_service
from app.services.saldo_service import saldo_service
from app.services.storage.imagekit_service import imagekit_service

router = APIRouter(prefix="/admin", tags=["🛠️ Administración"])


def _requiere_super_admin(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
) -> UsuarioActual:
    admin = db.query(Administrador).filter(Administrador.usuario_id == usuario.usuario_id).first()
    if not admin or admin.nivel != "super_admin":
        raise AuthorizationException(message="Esta accion requiere ser super_admin")
    return usuario


def _subir_archivo(archivo: UploadFile, carpeta: str) -> str:
    """Sube el archivo a ImageKit y devuelve la URL. Comun a fotos de conductor
    y de moto (solo maneja el storage, sin logica de negocio)."""
    if not imagekit_service.disponible:
        raise ValidationException(message="Storage no configurado (falta IMAGEKIT_PRIVATE_KEY)")
    contenido = _leer_archivo(archivo)
    resultado = imagekit_service.subir(
        file_content=contenido,
        file_name=archivo.filename or "foto.jpg",
        folder=carpeta,
    )
    if resultado is None:
        raise ValidationException(message="No se pudo subir el archivo")
    return resultado.url


async def _leer_archivo(archivo: UploadFile) -> bytes:
    contenido = await archivo.read()
    if not contenido:
        raise ValidationException(message="Archivo vacio")
    return contenido


@router.get("/conductores", response_model=list[ConductorOut])
async def listar_conductores(
    solo_pendientes: bool = False,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    return admin_service.listar_conductores(db, solo_pendientes=solo_pendientes)


@router.post("/conductores/{conductor_id}/aprobar", response_model=ConductorOut)
async def aprobar_conductor(
    conductor_id: int,
    aprobado: bool = True,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    return admin_service.aprobar_conductor(db, conductor_id, aprobado)


@router.get("/viajes", response_model=list[ViajeOut])
async def listar_viajes(
    estado: str | None = None,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    return admin_service.listar_viajes(db, estado=estado)


@router.get("/recargas", response_model=list[RecargaOut])
async def listar_recargas(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    return admin_service.listar_recargas(db)


@router.get("/paquetes", response_model=list[PaqueteOut])
async def listar_paquetes(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    return saldo_service.listar_paquetes(db)


@router.post("/paquetes", response_model=PaqueteOut)
async def crear_paquete(
    datos: PaqueteCreate,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_requiere_super_admin),
):
    return admin_service.crear_paquete(db, datos)


@router.put("/paquetes/{paquete_id}", response_model=PaqueteOut)
async def actualizar_paquete(
    paquete_id: int,
    datos: PaqueteUpdate,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(_requiere_super_admin),
):
    return admin_service.actualizar_paquete(db, paquete_id, datos)


@router.post("/conductores/{conductor_id}/foto", response_model=ConductorOut)
async def cargar_foto_conductor(
    conductor_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    """El admin sube/remplaza la foto de perfil del conductor."""
    url = _subir_archivo(archivo, f"hablavas/conductores/{conductor_id}")
    return admin_service.subir_foto_conductor(db, conductor_id, url)


@router.post("/conductores/{conductor_id}/moto-foto", response_model=ConductorOut)
async def cargar_foto_moto(
    conductor_id: int,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("administrador")),
):
    """El admin sube/remplaza la foto de la moto del conductor."""
    url = _subir_archivo(archivo, f"hablavas/conductores/{conductor_id}/moto")
    return admin_service.subir_foto_moto(db, conductor_id, url)
