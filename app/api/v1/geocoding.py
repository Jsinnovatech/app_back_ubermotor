from fastapi import APIRouter, Depends, Query

from app.core.security import requiere_tipo, UsuarioActual
from app.services.geocoding_service import geocoding_service

router = APIRouter(prefix="/geocoding", tags=["🗺️ Geocoding"])


@router.get("/search")
async def autocompletar(
    q: str = Query(description="Texto a buscar (desde 1 caracter)"),
    lat: float | None = Query(default=None),
    lng: float | None = Query(default=None),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor", "cliente", "administrador")),
):
    """Autocompletado de direcciones (Geoapify, filtrado a Peru). La key del
    proveedor vive en el backend, nunca en el front."""
    return await geocoding_service.autocompletar(q, lat=lat, lng=lng)


@router.get("/reverse")
async def reverse(
    lat: float = Query(),
    lng: float = Query(),
    usuario: UsuarioActual = Depends(requiere_tipo("conductor", "cliente", "administrador")),
):
    """Convierte una coordenada en direccion legible."""
    return {"direccion": await geocoding_service.reverse(lat, lng)}
