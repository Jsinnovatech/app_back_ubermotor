# Perfil 1:1 del conductor: extiende a Usuario. Tiene el saldo de carreras
# prepagado (regla de negocio: vigencia diaria, no acumulable).
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Conductor(Base):
    __tablename__ = "conductores"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, unique=True, index=True)
    nombre = Column(String(150), nullable=False)
    dni = Column(String(12), nullable=True)
    licencia = Column(String(30), nullable=True)
    foto_url = Column(String(500), nullable=True)
    rating_promedio = Column(Float, nullable=False, server_default="5.0")
    viajes_completados = Column(Integer, nullable=False, server_default="0")
    disponible = Column(Boolean, nullable=False, server_default="false")
    ubicacion_lat = Column(Float, nullable=True)
    ubicacion_lng = Column(Float, nullable=True)
    aprobado = Column(Boolean, nullable=False, server_default="false")

    # Saldo de carreras prepagadas: vale SOLO el dia de saldo_fecha.
    # Si saldo_fecha != hoy, el saldo se trata como 0 (no acumulable).
    saldo_carreras = Column(Integer, nullable=False, server_default="0")
    saldo_fecha = Column(DateTime(timezone=True), nullable=True)
    # Contador de rechazos del dia: cada RECHAZOS_PARA_DESCUENTO se resta 1 saldo.
    rechazos_hoy = Column(Integer, nullable=False, server_default="0")
    rechazos_fecha = Column(DateTime(timezone=True), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    usuario = relationship("Usuario", back_populates="conductor")
    vehiculo = relationship("Vehiculo", back_populates="conductor", uselist=False)
