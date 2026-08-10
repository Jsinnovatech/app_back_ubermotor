from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.viaje import Viaje
from app.schemas.viaje import ViajeOut
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/viajes", tags=["🛺 Viajes"])


def _cliente_de_usuario(db: Session, usuario_id: int) -> Cliente:
    from app.core.exceptions import NotFoundException

    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()
    if not cliente:
        raise NotFoundException(message="Perfil de cliente no encontrado")
    return cliente


def _conductor_de_usuario(db: Session, usuario_id: int) -> Conductor:
    from app.core.exceptions import NotFoundException

    conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()
    if not conductor:
        raise NotFoundException(message="Perfil de conductor no encontrado")
    return conductor


@router.get("/disponibles", response_model=list[ViajeOut])
async def viajes_disponibles(
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Viajes 'solicitado' que el conductor en linea puede aceptar."""
    return (
        db.query(Viaje)
        .filter(Viaje.estado == "solicitado")
        .order_by(Viaje.created_at.desc())
        .all()
    )


@router.post("/{viaje_id}/aceptar", response_model=ViajeOut)
async def aceptar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor acepta: consume 1 carrera de su saldo (falla si saldo 0)."""
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.aceptar(db, viaje_id, conductor.id)


@router.post("/{viaje_id}/rechazar", response_model=ViajeOut)
async def rechazar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor rechaza: cuenta para el descuento de 1 carrera cada 3 rechazos."""
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.rechazar(db, viaje_id, conductor.id)


@router.post("/{viaje_id}/iniciar", response_model=ViajeOut)
async def iniciar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    return viaje_service.iniciar(db, viaje_id)


@router.post("/{viaje_id}/completar", response_model=ViajeOut)
async def completar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    return viaje_service.completar(db, viaje_id)


@router.post("/{viaje_id}/cancelar", response_model=ViajeOut)
async def cancelar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente", "conductor")),
):
    """Cliente cancela -> la carrera se devuelve al saldo.
    Conductor cancela -> cuenta como rechazo (regla del -1/3)."""
    cliente = None
    conductor = None
    if usuario.tipo_usuario == "cliente":
        cliente = _cliente_de_usuario(db, usuario.usuario_id)
    else:
        conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.cancelar(db, viaje_id, quien="cliente" if cliente else "conductor")
