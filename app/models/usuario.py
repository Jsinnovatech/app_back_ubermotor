# Tabla base de usuarios: login unico (email+password) y tipo_usuario que
# decide que perfil 1:1 se lee (conductor/cliente/administrador). Mismo patron
# que la tabla unica de personal de Comanda.
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base

TIPOS_USUARIO = ("conductor", "cliente", "administrador", "serenazgo", "policia")


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    telefono = Column(String(20), nullable=True)
    # Nombre directo en la tabla base: conductor/cliente/admin lo tienen en su
    # perfil 1:1, pero serenazgo/policia (sin perfil extra) lo guardan aca.
    nombre = Column(String(150), nullable=True)
    tipo_usuario = Column(String(20), nullable=False, index=True)
    activo = Column(Boolean, nullable=False, server_default="true")
    verificado = Column(Boolean, nullable=False, server_default="false")
    refresh_token = Column(String(255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    conductor = relationship("Conductor", back_populates="usuario", uselist=False)
    cliente = relationship("Cliente", back_populates="usuario", uselist=False)
    administrador = relationship("Administrador", back_populates="usuario", uselist=False)
