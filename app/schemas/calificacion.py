from pydantic import BaseModel, Field


class CalificacionIn(BaseModel):
    puntaje: int = Field(ge=1, le=5, description="1-5 estrellas")
    comentario: str | None = None
