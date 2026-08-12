from pydantic import BaseModel


class ClienteOut(BaseModel):
    id: int
    nombre: str
    email: str | None = None
    foto_url: str | None = None
    viajes_realizados: int = 0
    rating_promedio: float = 5.0
