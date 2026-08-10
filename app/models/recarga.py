# Recarga (prepago) del conductor: compra un paquete de carreras para el dia.
# La acreditacion al saldo ocurre SOLO cuando el pago se confirma (estado acreditado).
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base

ESTADOS_RECARGA = ("pendiente", "acreditado", "rechazado")


class Recarga(Base):
    __tablename__ = "recargas"

    id = Column(Integer, primary_key=True, index=True)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=False, index=True)
    paquete_id = Column(Integer, ForeignKey("paquetes_carreras.id"), nullable=False)
    monto = Column(Integer, nullable=False)  # en soles
    carreras = Column(Integer, nullable=False)
    metodo = Column(String(20), nullable=False, server_default="yape")  # yape | efectivo | wallet
    estado = Column(String(20), nullable=False, server_default="pendiente")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
