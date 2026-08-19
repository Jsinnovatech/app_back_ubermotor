import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.security import SecurityService
from app.services.realtime_service import realtime_manager

router = APIRouter(tags=["⚡ Realtime"])


@router.websocket("/ws/conductores")
async def ws_conductores(websocket: WebSocket):
    """Conexion WebSocket del conductor: recibe viajes nuevos al instante.
    Autenticacion via query param ?token= (los WebSocket no usan headers HTTP
    de forma fiable desde Flutter web, asi que el token va en la URL)."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Falta token")
        return

    try:
        payload = SecurityService.verify_token(token)
    except Exception:
        await websocket.close(code=4401, reason="Token invalido")
        return

    if payload.get("tipo_usuario") != "conductor":
        await websocket.close(code=4403, reason="Solo conductores")
        return

    conductor_id = int(payload["sub"])
    await realtime_manager.conectar_conductor(conductor_id, websocket)
    try:
        while True:
            mensaje = await websocket.receive_text()
            try:
                if json.loads(mensaje).get("tipo") == "pong":
                    realtime_manager.registrar_pong("conductor", conductor_id)
            except ValueError:
                pass
    except WebSocketDisconnect:
        realtime_manager.desconectar_conductor(conductor_id)
    except Exception:
        realtime_manager.desconectar_conductor(conductor_id)


@router.websocket("/ws/clientes")
async def ws_clientes(websocket: WebSocket):
    """Conexion WebSocket del cliente: recibe la ubicacion en vivo del
    conductor de su viaje activo (tracking en el mapa)."""
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4401, reason="Falta token")
        return

    try:
        payload = SecurityService.verify_token(token)
    except Exception:
        await websocket.close(code=4401, reason="Token invalido")
        return

    if payload.get("tipo_usuario") != "cliente":
        await websocket.close(code=4403, reason="Solo clientes")
        return

    cliente_id = int(payload["sub"])
    await realtime_manager.conectar_cliente(cliente_id, websocket)
    try:
        while True:
            mensaje = await websocket.receive_text()
            try:
                if json.loads(mensaje).get("tipo") == "pong":
                    realtime_manager.registrar_pong("cliente", cliente_id)
            except ValueError:
                pass
    except WebSocketDisconnect:
        realtime_manager.desconectar_cliente(cliente_id)
    except Exception:
        realtime_manager.desconectar_cliente(cliente_id)
