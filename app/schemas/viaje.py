from pydantic import BaseModel, Field


class SolicitarViajeIn(BaseModel):
    origen_lat: float
    origen_lng: float
    destino_lat: float
    destino_lng: float
    origen_direccion: str | None = None
    destino_direccion: str | None = None
    tarifa: float = Field(ge=3.0, description="Tarifa minima 3 soles")
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
    tarifa: float
    metodo_pago_cliente: str

    class Config:
        from_attributes = True


class CancelarViajeIn(BaseModel):
    motivo: str | None = None
