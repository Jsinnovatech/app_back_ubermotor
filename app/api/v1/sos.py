from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.alerta_sos import AlertaSOS
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.schemas.auth import MensajeResponse
from app.services.sos_service import sos_service

router = APIRouter(prefix="/sos", tags=["🆘 SOS"])


class SosIn(BaseModel):
    lat: float
    lng: float


class SosOut(BaseModel):
    id: int
    origen: str
    estado: str
    message: str

    class Config:
        from_attributes = True


def _es_conductor(db: Session, usuario_id: int) -> bool:
    return db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first() is not None


@router.post("", response_model=SosOut)
async def activar_sos(
    datos: SosIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor", "cliente")),
):
    """Boton SOS. El front confirma con 2 presiones antes de llamar aca; este
    endpoint solo registra la alerta con todos los datos y dispara el webhook."""
    origen = "conductor" if usuario.tipo_usuario == "conductor" else "cliente"
    alerta = sos_service.crear(db, origen, usuario.usuario_id, datos.lat, datos.lng)
    return SosOut(
        id=alerta.id,
        origen=alerta.origen,
        estado=alerta.estado,
        message="Alerta SOS enviada a Serenazgo/Policia",
    )


@router.post("/{alerta_id}/cerrar", response_model=SosOut)
async def cerrar_sos(
    alerta_id: int,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("serenazgo", "policia", "administrador")),
):
    alerta = sos_service.cerrar(db, alerta_id)
    return SosOut(id=alerta.id, origen=alerta.origen, estado=alerta.estado, message="Alerta marcada como atendida")
