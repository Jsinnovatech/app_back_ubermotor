from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.core.exceptions import NotFoundException
from app.database import get_db
from app.models.recarga import Recarga
from app.schemas.recarga import PaqueteOut, RecargaOut, ComprarRecargaIn
from app.schemas.viaje import ViajeOut
from app.services.conductor_service import conductor_service
from app.services.realtime_service import realtime_manager
from app.services.saldo_service import saldo_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/recargas", tags=["💳 Recargas"])


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
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return saldo_service.comprar_recarga(db, conductor.id, datos.paquete_id, datos.metodo)


@router.post("/{recarga_id}/confirmar", response_model=RecargaOut)
async def confirmar_pago(
    recarga_id: int,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Confirma el pago (p.ej. verificacion manual del Yape) y acredita el saldo del dia."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    recarga = saldo_service.confirmar_recarga(db, recarga_id, conductor.id)
    # Con saldo recien acreditado, este conductor puede volver a aparecer en
    # "motos disponibles cerca": avisa a todos los clientes buscando moto.
    await realtime_manager.notificar_a_todos_los_clientes({"tipo": "conductores_actualizados"})
    return recarga


@router.get("/historial", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_conductor(db, conductor.id)
