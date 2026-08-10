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
    await realtime_manager.conectar(conductor_id, websocket)
    try:
        # El canal es de push: el conductor no envia mensajes, solo mantiene
        # la conexion abierta. receive_text mantiene vivo el handler.
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        realtime_manager.desconectar(conductor_id)
    except Exception:
        realtime_manager.desconectar(conductor_id)
