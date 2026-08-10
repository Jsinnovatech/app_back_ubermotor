# Tres tipos de usuario segun el login:
# - conductor: email+password (cuenta propia, cobra sus carreras).
# - cliente: email+password (cuenta propia, pide viajes).
# - administrador: email+password (super_admin = plataforma, admin = operador de zona).
# Igual que Comanda, el tipo_usuario va en el token y un dependency valida el rol.
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings
from app.core.exceptions import AuthenticationException

_bearer = HTTPBearer()


class SecurityService:
    @staticmethod
    def hash_password(password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    @staticmethod
    def verify_password(password: str, password_hash: str) -> bool:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))

    @staticmethod
    def create_access_token(usuario_id: int, tipo_usuario: str) -> str:
        expira = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        payload = {
            "sub": str(usuario_id),
            "tipo_usuario": tipo_usuario,
            "exp": expira,
        }
        return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> dict:
        try:
            return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        except JWTError:
            raise AuthenticationException(message="Token invalido o expirado")


class UsuarioActual:
    """Payload decodificado del token: identidad minima para autorizar sin pegarle a la BD."""

    def __init__(self, usuario_id: int, tipo_usuario: str):
        self.usuario_id = usuario_id
        self.tipo_usuario = tipo_usuario


def get_usuario_actual(credentials: HTTPAuthorizationCredentials = Depends(_bearer)) -> UsuarioActual:
    payload = SecurityService.verify_token(credentials.credentials)
    return UsuarioActual(
        usuario_id=int(payload["sub"]),
        tipo_usuario=payload["tipo_usuario"],
    )


def requiere_tipo(*tipos_permitidos: str):
    """Dependencia factory: valida que el usuario autenticado tenga uno de los tipos dados."""

    def _verificar(usuario: UsuarioActual = Depends(get_usuario_actual)) -> UsuarioActual:
        if usuario.tipo_usuario not in tipos_permitidos:
            from app.core.exceptions import AuthorizationException

            raise AuthorizationException(
                message=f"Esta accion requiere ser: {', '.join(tipos_permitidos)}"
            )
        return usuario

    return _verificar
