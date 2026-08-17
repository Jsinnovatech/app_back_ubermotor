import secrets
from datetime import datetime, timedelta, timezone

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import AuthenticationException, ValidationException
from app.core.security import SecurityService
from app.models.administrador import Administrador
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.schemas.auth import RegistroRequest
from app.services.email_service import email_service

MINUTOS_VALIDEZ_RESET = 15
_GOOGLE_TOKENINFO_URL = "https://oauth2.googleapis.com/tokeninfo"


class AuthService:
    """Registro y login unico para los tres perfiles. Un solo login, los
    perfiles se diferencian por tipo_usuario en la tabla usuarios (1:1)."""

    @staticmethod
    def registrar(db: Session, request: RegistroRequest) -> dict:
        if db.query(Usuario).filter(Usuario.email == request.email).first():
            raise AuthenticationException(message="Ya existe un usuario con ese email")

        usuario = Usuario(
            email=request.email,
            password_hash=SecurityService.hash_password(request.password),
            telefono=request.telefono,
            tipo_usuario=request.tipo_usuario,
        )
        db.add(usuario)
        db.flush()

        if request.tipo_usuario == "conductor":
            db.add(Conductor(usuario_id=usuario.id, nombre=request.nombre))
        elif request.tipo_usuario == "cliente":
            db.add(Cliente(usuario_id=usuario.id, nombre=request.nombre))
        elif request.tipo_usuario == "administrador":
            db.add(Administrador(usuario_id=usuario.id, nombre=request.nombre))
        elif request.tipo_usuario in ("serenazgo", "policia"):
            # No tienen perfil 1:1: el nombre vive en la tabla usuarios (email
            # como nombre base) y el rol decide que pantalla ven.
            usuario.nombre = request.nombre
        else:
            raise AuthenticationException(message="Tipo de usuario invalido")

        db.commit()

        token = SecurityService.create_access_token(usuario.id, request.tipo_usuario)
        return {
            "access_token": token,
            "usuario_id": usuario.id,
            "nombre": request.nombre,
            "tipo_usuario": request.tipo_usuario,
        }

    @staticmethod
    def login(db: Session, email: str, password: str) -> dict:
        usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.activo.is_(True)).first()
        if not usuario or not SecurityService.verify_password(password, usuario.password_hash):
            raise AuthenticationException(message="Email o contraseña invalidos")

        nombre = AuthService._nombre_de_perfil(db, usuario)
        token = SecurityService.create_access_token(usuario.id, usuario.tipo_usuario)
        return {
            "access_token": token,
            "usuario_id": usuario.id,
            "nombre": nombre,
            "tipo_usuario": usuario.tipo_usuario,
        }

    @staticmethod
    async def login_google(db: Session, id_token: str, tipo_usuario: str | None) -> dict:
        """Login/registro con Google. Verifica el id_token contra el propio
        Google (sin libreria extra: mismo patron httpx que push_service),
        confirma que es para esta app (aud == GOOGLE_CLIENT_ID) y que el
        email esta verificado. Si el email ya existe, es login directo
        (ignora tipo_usuario); si no existe, lo registra con el tipo_usuario
        que mando el front (obligatorio en ese caso, solo conductor/cliente:
        admin/serenazgo/policia no se autorregistran)."""
        try:
            async with httpx.AsyncClient(timeout=10) as cliente_http:
                resp = await cliente_http.get(_GOOGLE_TOKENINFO_URL, params={"id_token": id_token})
        except Exception:
            raise AuthenticationException(message="No se pudo validar el token de Google")

        if resp.status_code != 200:
            raise AuthenticationException(message="Token de Google invalido o expirado")

        info = resp.json()
        if info.get("aud") != settings.GOOGLE_CLIENT_ID:
            raise AuthenticationException(message="Token de Google no corresponde a esta app")
        if info.get("email_verified") not in ("true", True):
            raise AuthenticationException(message="El correo de Google no esta verificado")

        email = info["email"]
        usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.activo.is_(True)).first()

        if usuario is None:
            if tipo_usuario not in ("conductor", "cliente"):
                raise ValidationException(message="Cuenta nueva: falta indicar tipo_usuario (conductor o cliente)")
            nombre = info.get("name") or email.split("@")[0]
            # password_hash sigue siendo NOT NULL en la tabla: se guarda un
            # hash de un secreto aleatorio que nadie conoce, la cuenta solo
            # se puede usar via Google (no rompe el login por password).
            usuario = Usuario(
                email=email,
                password_hash=SecurityService.hash_password(secrets.token_urlsafe(32)),
                tipo_usuario=tipo_usuario,
                verificado=True,
            )
            db.add(usuario)
            db.flush()

            if tipo_usuario == "conductor":
                db.add(Conductor(usuario_id=usuario.id, nombre=nombre, foto_url=info.get("picture")))
            else:
                db.add(Cliente(usuario_id=usuario.id, nombre=nombre, foto_url=info.get("picture")))
            db.commit()

        nombre = AuthService._nombre_de_perfil(db, usuario)
        # Si el usuario ya existia sin foto, se la tomamos de Google.
        AuthService._actualizar_foto_si_falta(db, usuario, info.get("picture"))
        token = SecurityService.create_access_token(usuario.id, usuario.tipo_usuario)
        return {
            "access_token": token,
            "usuario_id": usuario.id,
            "nombre": nombre,
            "tipo_usuario": usuario.tipo_usuario,
        }

    @staticmethod
    def _actualizar_foto_si_falta(db: Session, usuario: Usuario, picture: str | None) -> None:
        if not picture:
            return
        if usuario.tipo_usuario == "conductor":
            perfil = db.query(Conductor).filter(Conductor.usuario_id == usuario.id).first()
            if perfil is not None and not perfil.foto_url:
                perfil.foto_url = picture
                db.commit()
            # Si el conductor tambien tiene perfil de pasajero, se la sincronizamos.
            pasajero = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
            if pasajero is not None and not pasajero.foto_url:
                pasajero.foto_url = picture
                db.commit()
        elif usuario.tipo_usuario == "cliente":
            perfil = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
            if perfil is not None and not perfil.foto_url:
                perfil.foto_url = picture
                db.commit()

    @staticmethod
    def _nombre_de_perfil(db: Session, usuario: Usuario) -> str:
        if usuario.tipo_usuario == "conductor":
            conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario.id).first()
            return conductor.nombre if conductor else usuario.email
        if usuario.tipo_usuario == "cliente":
            cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
            return cliente.nombre if cliente else usuario.email
        if usuario.tipo_usuario in ("serenazgo", "policia"):
            return usuario.nombre or usuario.email
        admin = db.query(Administrador).filter(Administrador.usuario_id == usuario.id).first()
        return admin.nombre if admin else usuario.email

    @staticmethod
    def solicitar_reset_password(db: Session, email: str) -> dict:
        # Respuesta generica siempre, exista o no el email, para no revelar
        # quien esta registrado (mismo criterio que Comanda/Casta de Gallos).
        mensaje_generico = {"message": "Si el email existe, recibiras un codigo para restablecer tu contraseña"}

        usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.activo.is_(True)).first()
        if not usuario:
            return mensaje_generico

        codigo = f"{secrets.randbelow(1_000_000):06d}"
        usuario.reset_code = codigo
        usuario.reset_code_expira = datetime.now(timezone.utc) + timedelta(minutes=MINUTOS_VALIDEZ_RESET)
        db.commit()

        nombre = AuthService._nombre_de_perfil(db, usuario)
        email_service.send_reset_password(to_email=email, nombre=nombre, codigo=codigo)
        return mensaje_generico

    @staticmethod
    def resetear_password(db: Session, email: str, codigo: str, nueva_password: str) -> dict:
        usuario = db.query(Usuario).filter(Usuario.email == email, Usuario.activo.is_(True)).first()
        if not usuario or usuario.reset_code != codigo:
            raise ValidationException(message="Codigo invalido o expirado")

        if not usuario.reset_code_expira or datetime.now(timezone.utc) > usuario.reset_code_expira:
            raise ValidationException(message="Codigo invalido o expirado")

        usuario.password_hash = SecurityService.hash_password(nueva_password)
        usuario.reset_code = None
        usuario.reset_code_expira = None
        db.commit()

        return {"message": "Contraseña actualizada exitosamente"}


auth_service = AuthService()
