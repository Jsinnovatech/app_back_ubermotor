from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.schemas.conductor import ConductorOut
from app.schemas.paquete import PaqueteCreate, PaqueteUpdate
from app.schemas.recarga import PaqueteOut, RecargaOut
from app.schemas.viaje import ViajeOut
from app.services.admin_service import admin_service

router = APIRouter(prefix="/admin", tags=["🛠️ Administración"])


def _requiere_super_admin(usuario: UsuarioActual = Depends(requiere_tipo("administrador"))) -> UsuarioActual:
    from app.models.administrador import Administrador
    from sqlalchemy.orm import Session
    from app.database import SessionLocal
    from app.core.exceptions import AuthorizationException

    db = SessionLocal()
    try:
        admin = db.query(Administrador).filter(Administrador.usuario_id == usuario.usuario_id).first()
        if not admin or admin.nivel != "super_admin":
            raise AuthorizationException(message="Esta accion requiere ser super_admin")
        return usuario
    finally:
        db.close()


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
    from app.services.saldo_service import saldo_service

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
