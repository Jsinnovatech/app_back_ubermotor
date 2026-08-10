from pydantic import BaseModel, Field


class PaqueteCreate(BaseModel):
    """Solo super_admin/admin crea paquetes: la regla "magica" de 10 carreras
    por 4 soles (0.40/carrera) vive en el catalogo, editable sin tocar codigo."""

    nombre: str = Field(min_length=2, max_length=50)
    monto: int = Field(gt=0, description="en soles: 2 / 4 / 8")
    carreras: int = Field(gt=0, description="5 / 10 / 20")


class PaqueteUpdate(BaseModel):
    nombre: str | None = None
    monto: int | None = Field(default=None, gt=0)
    carreras: int | None = Field(default=None, gt=0)
    activo: bool | None = None
