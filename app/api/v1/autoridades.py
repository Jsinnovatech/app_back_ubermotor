from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.alerta_sos import AlertaSOS
from app.models.conductor import Conductor
from app.models.viaje import Viaje

router = APIRouter(prefix="/autoridades", tags=["👮 Serenazgo / Policia"])


class AlertaSosOut(BaseModel):
    id: int
    origen: str
    nombre: str | None = None
    telefono: str | None = None
    email: str | None = None
    foto_url: str | None = None
    moto: str | None = None
    moto_foto_url: str | None = None
    seguro: str | None = None
    ubicacion_lat: float
    ubicacion_lng: float
    contraparte_nombre: str | None = None
    contraparte_telefono: str | None = None
    contraparte_foto_url: str | None = None
    contraparte_ubicacion_lat: float | None = None
    contraparte_ubicacion_lng: float | None = None
    estado: str
    viaje_id: int | None = None

    class Config:
        from_attributes = True


class UbicacionVivoOut(BaseModel):
    conductor_id: int
    lat: float
    lng: float


@router.get("/alertas", response_model=list[AlertaSosOut])
async def listar_alertas(
    estado: str = Query(default="activa"),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("serenazgo", "policia", "administrador")),
):
    """Serenazgo/Policia ven las alertas SOS activas con todos los datos:
    quien pidio ayuda, la contraparte, la moto (con foto), el seguro y la
    ubicacion."""
    return (
        db.query(AlertaSOS)
        .filter(AlertaSOS.estado == estado)
        .order_by(AlertaSOS.created_at.desc())
        .all()
    )


@router.get("/alertas/{alerta_id}/ubicacion-vivo", response_model=UbicacionVivoOut)
async def ubicacion_vivo(
    alerta_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("serenazgo", "policia", "administrador")),
):
    """Posicion ACTUAL del conductor de la alerta (para seguir la moto en
    movimiento en el mapa de la policia)."""
    alerta = db.query(AlertaSOS).filter(AlertaSOS.id == alerta_id).first()
    if not alerta or not alerta.viaje_id:
        raise NotFoundException(message="Alerta sin viaje activo")

    viaje = db.query(Viaje).filter(Viaje.id == alerta.viaje_id).first()
    if not viaje or not viaje.conductor_id:
        raise NotFoundException(message="Alerta sin conductor asignado")

    conductor = db.query(Conductor).filter(Conductor.id == viaje.conductor_id).first()
    if not conductor or conductor.ubicacion_lat is None:
        raise NotFoundException(message="Conductor sin ubicacion registrada")

    return UbicacionVivoOut(conductor_id=conductor.id, lat=conductor.ubicacion_lat, lng=conductor.ubicacion_lng)
