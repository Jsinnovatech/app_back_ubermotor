import logging

import httpx

logger = logging.getLogger(__name__)

GEOAPIFY_API = "https://api.geoapify.com/v1/geocode"


class GeocodingService:
    """Geocodificacion con Geoapify. La API key vive en el backend (variable
    de entorno GEOAPIFY_KEY), nunca en el front."""

    def __init__(self):
        from app.core.config import settings

        self._key = settings.GEOAPIFY_KEY

    @property
    def disponible(self) -> bool:
        return bool(self._key)

    async def autocompletar(self, query: str, lat: float | None = None, lng: float | None = None) -> list[dict]:
        """Sugerencias de lugares (desde 1 caracter), filtrado a Peru."""
        if not self.disponible or not query.strip():
            return []
        params = {
            "text": query.strip(),
            "apiKey": self._key,
            "limit": "5",
            "lang": "es",
            "country": "peru",
            "bias": f"proximity:{lng or -77.02824},{lat or -12.04318}",
        }
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{GEOAPIFY_API}/search", params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Geoapify autocomplete fallo: {e}")
            return []

        resultado = []
        for f in data.get("features", []):
            props = f.get("properties", {})
            geom = (f.get("geometry") or {}).get("coordinates") or [0, 0]
            resultado.append(
                {
                    "nombre": props.get("formatted") or "Ubicación",
                    "lat": geom[1],
                    "lng": geom[0],
                }
            )
        return resultado

    async def reverse(self, lat: float, lng: float) -> str | None:
        """Convierte una coordenada en direccion legible."""
        if not self.disponible:
            return None
        params = {"lat": str(lat), "lon": str(lng), "apiKey": self._key, "lang": "es"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(f"{GEOAPIFY_API}/reverse", params=params)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"Geoapify reverse fallo: {e}")
            return None

        features = data.get("features") or []
        if not features:
            return None
        return (features[0].get("properties") or {}).get("formatted")


geocoding_service = GeocodingService()
