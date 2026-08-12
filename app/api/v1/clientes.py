from fastapi import APIRouter, Depends, File, Query, UploadFile
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.core.exceptions import NotFoundException, ValidationException
from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.auth import MensajeResponse
from app.schemas.viaje import SolicitarViajeIn, ViajeOut
from app.services.realtime_service import realtime_manager
from app.services.storage.imagekit_service import imagekit_service
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
        payload = viaje_service._viaje_con_rider(db, viaje)
        payload["tipo"] = "viaje_nuevo"
        await realtime_manager.notificar_viaje(payload)
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


@router.post("/foto", response_model=MensajeResponse)
async def subir_foto(
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("cliente")),
):
    """El cliente sube su foto de perfil (la policia la ve en la Central SOS)."""
    if not imagekit_service.disponible:
        raise ValidationException(message="Storage no configurado")
    contenido = await archivo.read()
    if not contenido:
        raise ValidationException(message="Archivo vacio")

    resultado = imagekit_service.subir(
        file_content=contenido,
        file_name=archivo.filename or "foto.jpg",
        folder=f"hablavas/clientes/{usuario.usuario_id}",
    )
    if resultado is None:
        raise ValidationException(message="No se pudo subir el archivo")

    cliente = _cliente_de_usuario(db, usuario.usuario_id)
    cliente.foto_url = resultado.url
    db.commit()
    return {"message": "Foto de perfil actualizada"}
