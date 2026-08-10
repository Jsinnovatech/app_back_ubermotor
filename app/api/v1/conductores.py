from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, get_usuario_actual, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.schemas.conductor import (
    ConductorIn,
    ConductorOut,
    DisponibilidadIn,
    SaldoOut,
    UbicacionIn,
    VehiculoIn,
)
from app.schemas.recarga import PaqueteOut, RecargaOut, ComprarRecargaIn
from app.schemas.viaje import ViajeOut
from app.services.saldo_service import saldo_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/conductores", tags=["🛵 Conductores"])


def _conductor_de_usuario(db: Session, usuario_id: int) -> Conductor:
    from app.core.exceptions import NotFoundException

    conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario_id).first()
    if not conductor:
        raise NotFoundException(message="Perfil de conductor no encontrado")
    return conductor


@router.get("/perfil", response_model=ConductorOut)
async def mi_perfil(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    return _conductor_de_usuario(db, usuario.usuario_id)


@router.put("/perfil", response_model=ConductorOut)
async def actualizar_perfil(
    datos: ConductorIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.nombre = datos.nombre
    if datos.dni is not None:
        conductor.dni = datos.dni
    if datos.licencia is not None:
        conductor.licencia = datos.licencia
    if datos.vehiculo is not None:
        v = datos.vehiculo
        vehiculo = conductor.vehiculo
        if vehiculo is None:
            from app.models.vehiculo import Vehiculo

            vehiculo = Vehiculo(conductor_id=conductor.id)
            db.add(vehiculo)
        vehiculo.marca = v.marca or vehiculo.marca
        vehiculo.modelo = v.modelo or vehiculo.modelo
        vehiculo.placa = v.placa or vehiculo.placa
        vehiculo.color = v.color or vehiculo.color
    db.commit()
    db.refresh(conductor)
    return conductor


@router.put("/disponibilidad", response_model=ConductorOut)
async def cambiar_disponibilidad(
    datos: DisponibilidadIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.disponible = datos.disponible
    db.commit()
    db.refresh(conductor)
    return conductor


@router.put("/ubicacion")
async def actualizar_ubicacion(
    datos: UbicacionIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    conductor.ubicacion_lat = datos.lat
    conductor.ubicacion_lng = datos.lng
    db.commit()
    return {"message": "Ubicacion actualizada"}


@router.get("/saldo", response_model=SaldoOut)
async def mi_saldo(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return {
        "conductor_id": conductor.id,
        "saldo_carreras": saldo_service.saldo_actual(db, conductor.id),
        "saldo_fecha": conductor.saldo_fecha.isoformat() if conductor.saldo_fecha else None,
    }


@router.get("/paquetes", response_model=list[PaqueteOut])
async def listar_paquetes(db: Session = Depends(get_db)):
    return saldo_service.listar_paquetes(db)


@router.post("/recargar", response_model=RecargaOut)
async def recargar(
    datos: ComprarRecargaIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Compra un paquete (2/4/8 soles). Queda 'pendiente' hasta confirmar el pago."""
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return saldo_service.comprar_recarga(db, conductor.id, datos.paquete_id, datos.metodo)


@router.get("/historial", response_model=list[ViajeOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = _conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_conductor(db, conductor.id)
