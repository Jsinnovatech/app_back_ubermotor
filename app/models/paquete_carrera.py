# Catalogo de paquetes de carreras prepagadas. Regla "magica":
# 10 carreras por 4 soles (0.40 soles/carrera). Editable por admin sin tocar codigo.
from sqlalchemy import Boolean, Column, DateTime, Integer, String, func

from app.database import Base


class PaqueteCarrera(Base):
    __tablename__ = "paquetes_carreras"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(50), nullable=False)
    monto = Column(Integer, nullable=False)  # en soles: 2 / 4 / 8
    carreras = Column(Integer, nullable=False)  # 5 / 10 / 20
    activo = Column(Boolean, nullable=False, server_default="true")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
