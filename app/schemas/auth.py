from pydantic import BaseModel, Field, EmailStr


class RegistroRequest(BaseModel):
    """Registro base comun a los tres perfiles. El tipo_usuario decide que
    perfil 1:1 se crea y que pantalla ve el front (patron _Portero)."""

    email: EmailStr
    password: str = Field(min_length=8, max_length=100)
    telefono: str | None = None
    tipo_usuario: str  # conductor | cliente | administrador
    nombre: str = Field(min_length=2, max_length=150)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nombre: str
    tipo_usuario: str


class MensajeResponse(BaseModel):
    message: str
