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


class GoogleLoginRequest(BaseModel):
    """id_token que entrega el SDK de Google Sign-In en el front. tipo_usuario
    solo hace falta la primera vez (cuenta nueva); si el email ya existe se
    ignora y se usa el tipo_usuario ya registrado."""

    id_token: str
    tipo_usuario: str | None = None  # conductor | cliente (autoservicio; admin/serenazgo/policia no)


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    usuario_id: int
    nombre: str
    tipo_usuario: str


class MensajeResponse(BaseModel):
    message: str


class SolicitarResetRequest(BaseModel):
    email: EmailStr


class ResetearPasswordRequest(BaseModel):
    email: EmailStr
    codigo: str
    nueva_password: str = Field(min_length=8, max_length=100)
