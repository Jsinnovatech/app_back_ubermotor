from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundException
from app.models.conductor import Conductor
from app.models.paquete_carrera import PaqueteCarrera
from app.models.recarga import Recarga
from app.models.usuario import Usuario
from app.models.viaje import Viaje


class AdminService:
    """Gestion del administrador (super_admin = todo, admin = operador de zona).
    La autorizacion por nivel se valida en el router con requiere_tipo + check de nivel."""

    @staticmethod
    def aprobar_conductor(db: Session, conductor_id: int, aprobado: bool = True) -> Conductor:
        conductor = db.query(Conductor).filter(Conductor.id == conductor_id).first()
        if not conductor:
            raise NotFoundException(message="Conductor no encontrado")
        conductor.aprobado = aprobado
        db.commit()
        db.refresh(conductor)
        return conductor

    @staticmethod
    def listar_conductores(db: Session, solo_pendientes: bool = False) -> list[Conductor]:
        q = db.query(Conductor).order_by(Conductor.created_at.desc())
        if solo_pendientes:
            q = q.filter(Conductor.aprobado.is_(False))
        return q.all()

    @staticmethod
    def listar_usuarios(db: Session) -> list[Usuario]:
        return db.query(Usuario).order_by(Usuario.created_at.desc()).all()

    @staticmethod
    def activar_usuario(db: Session, usuario_id: int, activo: bool) -> Usuario:
        usuario = db.query(Usuario).filter(Usuario.id == usuario_id).first()
        if not usuario:
            raise NotFoundException(message="Usuario no encontrado")
        usuario.activo = activo
        db.commit()
        db.refresh(usuario)
        return usuario

    @staticmethod
    def crear_paquete(db: Session, datos) -> PaqueteCarrera:
        paquete = PaqueteCarrera(
            nombre=datos.nombre,
            monto=datos.monto,
            carreras=datos.carreras,
        )
        db.add(paquete)
        db.commit()
        db.refresh(paquete)
        return paquete

    @staticmethod
    def actualizar_paquete(db: Session, paquete_id: int, datos) -> PaqueteCarrera:
        paquete = db.query(PaqueteCarrera).filter(PaqueteCarrera.id == paquete_id).first()
        if not paquete:
            raise NotFoundException(message="Paquete no encontrado")
        if datos.nombre is not None:
            paquete.nombre = datos.nombre
        if datos.monto is not None:
            paquete.monto = datos.monto
        if datos.carreras is not None:
            paquete.carreras = datos.carreras
        if datos.activo is not None:
            paquete.activo = datos.activo
        db.commit()
        db.refresh(paquete)
        return paquete

    @staticmethod
    def listar_recargas(db: Session) -> list[Recarga]:
        return db.query(Recarga).order_by(Recarga.created_at.desc()).limit(100).all()

    @staticmethod
    def listar_viajes(db: Session, estado: str | None = None) -> list[Viaje]:
        q = db.query(Viaje).order_by(Viaje.created_at.desc())
        if estado:
            q = q.filter(Viaje.estado == estado)
        return q.limit(100).all()


admin_service = AdminService()
