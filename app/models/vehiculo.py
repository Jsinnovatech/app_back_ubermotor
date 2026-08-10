from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class Vehiculo(Base):
    __tablename__ = "vehiculos"

    id = Column(Integer, primary_key=True, index=True)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=False, unique=True, index=True)
    marca = Column(String(50), nullable=True)
    modelo = Column(String(50), nullable=True)
    placa = Column(String(15), nullable=True)
    color = Column(String(30), nullable=True)
    foto_url = Column(String(500), nullable=True)
    soat_vencimiento = Column(Date, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    conductor = relationship("Conductor", back_populates="vehiculo")
