from sqlalchemy.orm import Session

from app.core.exceptions import AuthenticationException
from app.core.security import SecurityService
from app.models.administrador import Administrador
from app.models.cliente import Cliente
from app.models.conductor import Conductor
from app.models.usuario import Usuario
from app.schemas.auth import RegistroRequest


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
    def _nombre_de_perfil(db: Session, usuario: Usuario) -> str:
        if usuario.tipo_usuario == "conductor":
            conductor = db.query(Conductor).filter(Conductor.usuario_id == usuario.id).first()
            return conductor.nombre if conductor else usuario.email
        if usuario.tipo_usuario == "cliente":
            cliente = db.query(Cliente).filter(Cliente.usuario_id == usuario.id).first()
            return cliente.nombre if cliente else usuario.email
        admin = db.query(Administrador).filter(Administrador.usuario_id == usuario.id).first()
        return admin.nombre if admin else usuario.email


auth_service = AuthService()
