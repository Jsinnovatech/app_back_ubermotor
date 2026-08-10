from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.security import get_usuario_actual, UsuarioActual
from app.database import get_db
from app.schemas.auth import LoginRequest, LoginResponse, MensajeResponse, RegistroRequest
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


@router.get("/me", response_model=MensajeResponse)
async def me(usuario: UsuarioActual = Depends(get_usuario_actual)):
    """Valida el token y devuelve la identidad del usuario autenticado."""
    return {"message": f"Autenticado como {usuario.tipo_usuario} (id={usuario.usuario_id})"}
