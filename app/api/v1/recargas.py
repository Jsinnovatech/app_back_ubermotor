from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.conductor import Conductor
from app.schemas.recarga import PaqueteOut, RecargaOut, ComprarRecargaIn
from app.schemas.viaje import ViajeOut
from app.services.saldo_service import saldo_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/recargas", tags=["💳 Recargas"])


def _conductor_de_usuario(db: Session, usuario_id: int) -> Conductor:
    from app.core.exceptions import NotFoundException

    conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()
    if not conductor:
        raise NotFoundException(message="Perfil de conductor no encontrado")
    return conductor


@router.get("/paquetes", response_model=list[PaqueteOut])
async def listar_paquetes(db: Session = Depends(get_db)):
    """Catalogo publico de paquetes: 2/5, 4/10, 8/20 (regla 0.40/carrera)."""
    return saldo_service.listar_paquetes(db)


@router.post("/comprar", response_model=RecargaOut)
async def comprar(
    datos: ComprarRecargaIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return saldo_service.comprar_recarga(db, conductor.id, datos.paquete_id, datos.metodo)


@router.post("/{recarga_id}/confirmar", response_model=RecargaOut)
async def confirmar_pago(
    recarga_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Confirma el pago (p.ej. verificacion manual del Yape) y acredita el saldo del dia."""
    from app.models.recarga import Recarga
    from app.core.exceptions import NotFoundException

    recarga = db.query(Recarga).filter(Recarga.id == recarga_id).first()
    if not recarga:
        raise NotFoundException(message="Recarga no encontrada")

    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    if recarga.conductor_id != conductor.id:
        raise NotFoundException(message="Recarga no encontrada")

    saldo_service.acreditar_recarga(db, conductor.id)
    db.refresh(recarga)
    return recarga


@router.get("/historial", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_conductor(db, conductor.id)
