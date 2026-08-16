from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_usuario_actual, UsuarioActual
from app.database import get_db
from app.schemas.auth import (
    GoogleLoginRequest,
    LoginRequest,
    LoginResponse,
    MensajeResponse,
    RegistroRequest,
    ResetearPasswordRequest,
    SolicitarResetRequest,
)
from app.services.auth_service import auth_service

router = APIRouter(prefix="/auth", tags=["🔐 Autenticación"])


@router.post("/registro", response_model=LoginResponse)
async def registrar(request: RegistroRequest, db: Session = Depends(get_db)):
    """Registro unico: conductor, cliente o administrador (tipo_usuario)."""
    return auth_service.registrar(db, request)


@router.post("/login", response_model=LoginResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """Login por email+password para los tres perfiles."""
    return auth_service.login(db, request.email, request.password)


@router.post("/google", response_model=LoginResponse)
async def login_google(request: GoogleLoginRequest, db: Session = Depends(get_db)):
    """Login/registro con Google. Si el email ya existe hace login directo;
    si es cuenta nueva, la crea (requiere tipo_usuario: conductor o cliente)."""
    return await auth_service.login_google(db, request.id_token, request.tipo_usuario)


@router.post("/solicitar-reset", response_model=MensajeResponse)
async def solicitar_reset(request: SolicitarResetRequest, db: Session = Depends(get_db)):
    """Envia un codigo de 6 digitos por correo para restablecer la contraseña."""
    return auth_service.solicitar_reset_password(db, request.email)


@router.post("/resetear-password", response_model=MensajeResponse)
async def resetear_password(request: ResetearPasswordRequest, db: Session = Depends(get_db)):
    """Confirma el codigo recibido por correo y establece la nueva contraseña."""
    return auth_service.resetear_password(db, request.email, request.codigo, request.nueva_password)


@router.get("/me", response_model=MensajeResponse)
async def me(usuario: UsuarioActual = Depends(get_usuario_actual)):
    """Valida el token y devuelve la identidad del usuario autenticado."""
    return {"message": f"Autenticado como {usuario.tipo_usuario} (id={usuario.usuario_id})"}
