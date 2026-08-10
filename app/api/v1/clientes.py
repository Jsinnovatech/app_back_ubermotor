from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.auth import MensajeResponse
from app.schemas.viaje import SolicitarViajeIn, ViajeOut
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/clientes", tags=["🙋 Clientes"])


def _cliente_de_usuario(db: Session, usuario_id: int) -> Cliente:
    from app.core.exceptions import NotFoundException

    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()
    if not cliente:
        raise NotFoundException(message="Perfil de cliente no encontrado")
    return cliente


@router.post("/viajes", response_model=ViajeOut)
async def solicitar_viaje(
    datos: SolicitarViajeIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    """Pide un viaje. Tarifa minima 3 soles, pago directo al conductor (Yape/efectivo)."""
    cliente = _cliente_de_usuario(db, usuario.usuario_id)
    return viaje_service.solicitar(db, cliente.id, datos)


@router.get("/viajes", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    cliente = _cliente_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_cliente(db, cliente.id)
