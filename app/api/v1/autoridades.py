from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.alerta_sos import AlertaSOS
from app.services.sos_service import sos_service

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
    return sos_service.listar_alertas(db, estado=estado)


@router.get("/alertas/{alerta_id}/ubicacion-vivo", response_model=UbicacionVivoOut)
async def ubicacion_vivo(
    alerta_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("serenazgo", "policia", "administrador")),
):
    """Posicion ACTUAL del conductor de la alerta (para seguir la moto en
    movimiento en el mapa de la policia)."""
    return UbicacionVivoOut(**sos_service.ubicacion_vivo_conductor(db, alerta_id))
