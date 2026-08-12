from datetime import datetime

from pydantic import BaseModel, Field


class VehiculoIn(BaseModel):
    marca: str | None = None
    modelo: str | None = None
    placa: str | None = None
    color: str | None = None
    soat_vencimiento: str | None = None


class ConductorIn(BaseModel):
    nombre: str = Field(min_length=2, max_length=150)
    dni: str | None = None
    licencia: str | None = None
    vehiculo: VehiculoIn | None = None


class UbicacionIn(BaseModel):
    lat: float
    lng: float


class DisponibilidadIn(BaseModel):
    disponible: bool


class ConductorOut(BaseModel):
    id: int
    nombre: str
    dni: str | None = None
    dni_foto_url: str | None = None
    licencia: str | None = None
    licencia_foto_url: str | None = None
    foto_url: str | None = None
    antecedentes_foto_url: str | None = None
    antecedentes_valido: bool | None = None
    rating_promedio: float
    viajes_completados: int
    disponible: bool
    aprobado: bool
    saldo_carreras: int
    saldo_fecha: datetime | None = None
    ingreso_hoy: float = 0.0

    class Config:
        from_attributes = True


class SaldoOut(BaseModel):
    conductor_id: int
    saldo_carreras: int
    saldo_fecha: datetime | None = None
