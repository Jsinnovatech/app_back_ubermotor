from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.schemas.auth import MensajeResponse
from app.services.calificacion_service import calificacion_service

router = APIRouter(prefix="/calificaciones", tags=["⭐ Calificaciones y ranking"])


class CalificarIn(BaseModel):
    viaje_id: int
    puntaje: int = Field(ge=1, le=5, description="1-5 estrellas")
    comentario: str | None = Field(default=None, max_length=300)


class RankingItemOut(BaseModel):
    conductor_id: int
    nombre: str
    rating_promedio: float
    viajes_completados: int
    foto_url: str | None = None


@router.post("", response_model=MensajeResponse)
async def calificar(
    datos: CalificarIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor", "cliente")),
):
    """Califica un viaje completado (1-5). Si el cliente califica, el puntaje
    alimenta el rating del conductor (ranking)."""
    calificacion_service.calificar(db, datos.viaje_id, usuario.usuario_id, datos.puntaje, datos.comentario)
    return {"message": "Calificacion registrada"}


@router.get("/ranking", response_model=list[RankingItemOut])
async def ranking(
    top: int = 20,
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("cliente", "conductor", "administrador")),
):
    """Ranking de conductores por rating (con desempate por viajes)."""
    return calificacion_service.ranking(db, top)
