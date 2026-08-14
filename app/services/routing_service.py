import logging

import httpx

logger = logging.getLogger(__name__)

# OSRM: servicio de routing publico y gratuito (sin API key), el mismo que
# usan muchas apps de transporte. Devuelve la ruta por calles entre dos puntos.
OSRM_ENDPOINT = "https://router.project-osrm.org/route/v1/driving"


class RoutingService:
    @staticmethod
    async def ruta(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> list[dict] | None:
        """Calcula la ruta real por calles entre dos puntos. Devuelve la lista
        de {lat, lng} de la polilinea, o None si OSRM no responde."""
        url = (
            f"{OSRM_ENDPOINT}/{lng_a},{lat_a};{lng_b},{lat_b}"
            "?overview=full&geometries=geojson"
        )
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                resp.raise_for_status()
                data = resp.json()
        except Exception as e:
            logger.error(f"OSRM fallo: {e}")
            return None

        if not data or not data.get("routes"):
            return None

        coords = data["routes"][0].get("geometry", {}).get("coordinates", [])
        # OSRM devuelve [lng, lat]; convertimos a {lat, lng} para el front.
        return [{"lat": c[1], "lng": c[0]} for c in coords]


routing_service = RoutingService()
