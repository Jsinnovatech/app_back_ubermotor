from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.orm import Session

from app.core.security import requiere_tipo, UsuarioActual
from app.database import get_db
from app.models.cliente import Cliente
from app.schemas.conductor import (
    ConductorIn,
    ConductorOut,
    DisponibilidadIn,
    SaldoOut,
    UbicacionIn,
)
from app.schemas.recarga import PaqueteOut, RecargaOut, ComprarRecargaIn
from app.schemas.viaje import ViajeConRiderOut
from app.services.conductor_service import conductor_service
from app.services.realtime_service import realtime_manager
from app.services.saldo_service import saldo_service
from app.services.viaje_service import viaje_service

router = APIRouter(prefix="/conductores", tags=["🛵 Conductores"])


@router.post("/perfil-pasajero")
async def activar_modo_pasajero(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El conductor activa el modo pasajero (como InDrive): se crea su perfil de
    cliente si no existe. Asi la misma cuenta puede pedir carreras como pasajero
    sin perder su perfil de conductor."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.usuario_id).first()
    if cliente is None:
        cliente = Cliente(usuario_id=usuario.usuario_id, nombre=conductor.nombre, foto_url=conductor.foto_url)
        db.add(cliente)
        db.commit()
        db.refresh(cliente)
    else:
        # Si el cliente no tiene foto, se la pasamos del conductor.
        if not cliente.foto_url and conductor.foto_url:
            cliente.foto_url = conductor.foto_url
            db.commit()
    return {"id": cliente.id, "nombre": cliente.nombre, "pasajero_activo": True}


@router.post("/documentos", response_model=ConductorOut)
async def subir_documento(
    tipo: str,
    cara: str | None = None,
    archivo: UploadFile = File(...),
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Sube un documento del conductor a ImageKit. tipo: foto | dni | brevete |
    soat | moto. cara: frente | dorso (solo dni y brevete). El admin revisa
    todos los documentos y recien ahi aprueba al conductor."""
    return await conductor_service.subir_documento(db, usuario.usuario_id, tipo, cara, archivo)


@router.get("/documentos")
async def mis_documentos(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Documentos del conductor subidos (tipo, cara, url). El perfil usa esto
    para saber si le falta algo, no los campos viejos dni_foto_url/etc."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return conductor_service.documentos_de_conductor(db, conductor.id)


@router.get("/perfil", response_model=ConductorOut)
async def mi_perfil(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """Perfil del conductor. El saldo respeta la vigencia diaria (no acumulable):
    si saldo_fecha es de otro dia, se reporta 0."""
    return conductor_service.perfil_con_saldo(db, usuario.usuario_id)


@router.put("/perfil", response_model=ConductorOut)
async def actualizar_perfil(
    datos: ConductorIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    return conductor_service.actualizar_perfil(db, usuario.usuario_id, datos)


@router.put("/disponibilidad", response_model=ConductorOut)
async def cambiar_disponibilidad(
    datos: DisponibilidadIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = conductor_service.cambiar_disponibilidad(db, usuario.usuario_id, datos.disponible)
    # Se prendio o apago en el mapa: avisa a todos los clientes buscando moto
    # para que refresquen "motos disponibles cerca" al instante.
    await realtime_manager.notificar_a_todos_los_clientes({"tipo": "conductores_actualizados"})
    return conductor


@router.put("/ubicacion")
async def actualizar_ubicacion(
    datos: UbicacionIn,
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    await conductor_service.actualizar_ubicacion(db, usuario.usuario_id, datos.lat, datos.lng)
    return {"message": "Ubicacion actualizada"}


@router.get("/saldo", response_model=SaldoOut)
async def mi_saldo(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
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
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return saldo_service.comprar_recarga(db, conductor.id, datos.paquete_id, datos.metodo)


@router.get("/historial", response_model=list[ViajeConRiderOut])
async def historial(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.historial_conductor(db, conductor.id)


@router.get("/viaje-activo", response_model=ViajeConRiderOut | None)
async def viaje_activo(
    db: Session = Depends(get_db),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor")),
):
    """El viaje en curso del conductor (asignado/llegado/en_curso). Si no tiene
    ninguno activo devuelve null. Lo usa el front para la pantalla de carrera."""
    conductor = conductor_service.conductor_de_usuario(db, usuario.usuario_id)
    return viaje_service.viaje_activo_de_conductor(db, conductor.id)
