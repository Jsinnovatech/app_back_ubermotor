from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.auth import MensajeResponse
from app.schemas.viaje import SolicitarViajeIn, ViajeOut
from app.services.realtime_service import realtime_manager
from app.services.viaje_service import conductores_disponibles_cerca, viaje_service

router = APIRouter(prefix="/clientes", tags=["🙋 Clientes"])


def _cliente_de_usuario(db: Session, usuario_id: int) -> Cliente:
    from app.core.exceptions import NotFoundException

    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario_id).first()
    if not cliente:
        raise NotFoundException(message="Perfil de cliente no encontrado")
    return cliente


@router.get("/conductores-disponibles")
async def conductores_disponibles(
    lat: float = Query(...),
    lng: float = Query(...),
    radio_km: float = Query(default=5.0),
    db: Session = Depends(get_db),
    _usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    """Motos disponibles cerca del cliente (conductor aprobado + disponible +
    con saldo), con reputacion (rating, viajes) para decidir."""
    return conductores_disponibles_cerca(db, lat, lng, radio_km)


@router.post("/viajes", response_model=ViajeOut)
async def solicitar_viaje(
    datos: SolicitarViajeIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    """Pide un viaje. Tarifa minima 3 soles, pago directo al conductor (Yape/efectivo).
    Apenas se crea, se EMPUJA a los conductores conectados por WebSocket (<1s)."""
    cliente = _cliente_de_usuario(db, usuario.usuario_id)
    viaje = viaje_service.solicitar(db, cliente.id, datos)

    try:
        await realtime_manager.notificar_viaje({
            "tipo": "viaje_nuevo",
            "viaje_id": viaje.id,
            "cliente_id": viaje.cliente_id,
            "origen_lat": viaje.origen_lat,
            "origen_lng": viaje.origen_lng,
            "destino_lat": viaje.destino_lat,
            "destino_lng": viaje.destino_lng,
            "origen_direccion": viaje.origen_direccion,
            "destino_direccion": viaje.destino_direccion,
            "tarifa": viaje.tarifa,
            "metodo_pago_cliente": viaje.metodo_pago_cliente,
        })
    except Exception:
        # Si falla el push, el polling del front sigue siendo el fallback.
        pass

    return viaje


@router.get("/viajes", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    cliente = _cliente_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_cliente(db, cliente.id)
