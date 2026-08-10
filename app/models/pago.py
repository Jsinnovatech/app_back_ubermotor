# Pagos (referencia Mercado Pago). Registra el metodo y estado del pago del
# viaje, y referencia_externa si se integra un proveedor externo por webhook.
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base

ESTADOS_PAGO = ("pendiente", "pagado", "reembolsado")


class Pago(Base):
    __tablename__ = "pagos"

    id = Column(Integer, primary_key=True, index=True)
    viaje_id = Column(Integer, ForeignKey("viajes.id"), nullable=False, index=True)
    metodo = Column(String(20), nullable=False, server_default="efectivo")  # yape | efectivo | wallet
    monto = Column(Float, nullable=False)
    estado = Column(String(20), nullable=False, server_default="pendiente")
    referencia_externa = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
