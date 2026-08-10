# Perfil 1:1 del administrador. Dos niveles como Comanda:
# - super_admin: dueno de la plataforma (ve todo).
# - admin: operador de una zona/ciudad.
from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base

NIVELES_ADMIN = ("super_admin", "admin")


class Administrador(Base):
    __tablename__ = "administradores"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    nombre = Column(String(150), nullable=False)
    nivel = Column(String(20), nullable=False, server_default="admin")
    zona = Column(String(100), nullable=True)
    recibe_notificaciones = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="administrador")
