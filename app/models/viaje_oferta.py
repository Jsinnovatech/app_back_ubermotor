# Oferta de un conductor sobre un viaje en estado 'solicitado' (patron InDrive).
# El conductor NO acepta la carrera: ofrece un precio. El cliente elige una
# oferta entre las propuestas (de a 3). El saldo se consume al ACEPTAR la oferta
# (Opcion A), no al ofertar.
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base

ESTADOS_OFERTA = ("activa", "aceptada", "vencida", "retirada")


class ViajeOferta(Base):
    __tablename__ = "viaje_ofertas"

    id = Column(Integer, primary_key=True, index=True)
    viaje_id = Column(Integer, ForeignKey("viajes.id"), nullable=False, index=True)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=False, index=True)
    precio_ofertado = Column(Float, nullable=False)
    estado = Column(String(20), nullable=False, server_default="activa", index=True)
    # Opcional: control server-side del plazo (30s) para vencer ofertas viejas.
    vence_en = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)