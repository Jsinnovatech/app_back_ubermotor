from pydantic import BaseModel, Field


class SolicitarViajeIn(BaseModel):
    origen_lat: float
    origen_lng: float
    destino_lat: float
    destino_lng: float
    origen_direccion: str | None = None
    destino_direccion: str | None = None
    tarifa: float | None = Field(
        default=None, ge=3.0, description="Tarifa de piso (referencia). Opcional: el precio real sale de la oferta del conductor"
    )
    metodo_pago_cliente: str = Field(default="yape", pattern="^(yape|efectivo)$")


class AsignarViajeIn(BaseModel):
    conductor_id: int


class ViajeOut(BaseModel):
    id: int
    cliente_id: int
    conductor_id: int | None = None
    estado: str
    origen_lat: float
    origen_lng: float
    destino_lat: float
    destino_lng: float
    origen_direccion: str | None = None
    destino_direccion: str | None = None
    tarifa: float
    metodo_pago_cliente: str

    class Config:
        from_attributes = True


class ViajeConRiderOut(ViajeOut):
    """Viaje como lo ve el conductor: incluye quien es el rider (nombre y
    puntuacion) para decidir si tomarlo."""

    rider_nombre: str | None = None
    rider_rating: float | None = None
    rider_foto_url: str | None = None


class CancelarViajeIn(BaseModel):
    motivo: str | None = None


class CrearOfertaIn(BaseModel):
    precio_ofertado: float = Field(ge=3.0, description="Precio ofertado por el conductor, minimo 3 soles")


class ViajeOfertaOut(BaseModel):
    id: int
    viaje_id: int
    conductor_id: int
    precio_ofertado: float
    estado: str
    created_at: str | None = None

    class Config:
        from_attributes = True


class OfertaConConductorOut(ViajeOfertaOut):
    """Oferta como la ve el cliente al elegir: incluye el conductor (nombre,
    rating, foto, moto, distancia y ETA aproximada al origen)."""

    conductor_nombre: str | None = None
    conductor_rating: float | None = None
    conductor_foto_url: str | None = None
    moto_descripcion: str | None = None
    moto_placa: str | None = None
    distancia_km: float | None = None
    eta_minutos: int | None = None
