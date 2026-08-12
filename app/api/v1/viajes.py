from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.models.viaje import Viaje
from app.schemas.viaje import ViajeConRiderOut, ViajeOut
from app.services.conductor_service import conductor_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/viajes", tags=["🛺 Viajes"])


def _cliente_de_usuario(db: Session, usuario_id: int) -> Cliente:
    from app.core.exceptions import NotFoundException

    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()
    if not cliente:
        raise NotFoundException(message="Perfil de cliente no encontrado")
    return cliente


@router.get("/disponibles", response_model=list[ViajeConRiderOut])
async def viajes_disponibles(
    lat: float | None = Query(default=None, description="Latitud del conductor"),
    lng: float | None = Query(default=None, description="Longitud del conductor"),
    radio_km: float = Query(default=5.0, description="Radio de busqueda en km"),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Viajes 'solicitado' con la info del rider (nombre + puntuacion). Si se
    pasan lat/lng, solo devuelve los viajes cuyo ORIGEN esta dentro del radio."""
    return viaje_service.disponibles_cerca(db, lat=lat, lng=lng, radio_km=radio_km)


@router.get("/{viaje_id}", response_model=ViajeConRiderOut)
async def detalle_viaje(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor", "cliente")),
):
    """Estado actual de un viaje (lo usa el cliente en el seguimiento y el
    conductor para refrescar la carrera en curso)."""
    return viaje_service.detalle(db, viaje_id)


@router.post("/{viaje_id}/aceptar", response_model=ViajeOut)
async def aceptar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor acepta: consume 1 carrera de su saldo (falla si saldo 0)."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.aceptar(db, viaje_id, conductor.id)


@router.post("/{viaje_id}/rechazar", response_model=ViajeOut)
async def rechazar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor rechaza: cuenta para el descuento de 1 carrera cada 3 rechazos."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.rechazar(db, viaje_id, conductor.id)


@router.post("/{viaje_id}/iniciar", response_model=ViajeOut)
async def iniciar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    return viaje_service.iniciar(db, viaje_id)


@router.post("/{viaje_id}/llegar", response_model=ViajeOut)
async def llegar(
    viaje_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor llego al punto de recogida: el viaje pasa a 'llegado' y el
    cliente ve 'Tu conductor esta esperando'."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.llegar(db, viaje_id, conductor.id)


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
        conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.cancelar(db, viaje_id, quien="cliente" if cliente else "conductor")
