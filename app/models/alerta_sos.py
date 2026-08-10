# Alerta de emergencia (SOS): se crea cuando un conductor o cliente presiona
# el boton SOS 2 veces. Serenazgo/Policia la ven con los datos del involucrado
# y la ubicacion en tiempo real.
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base

ESTADOS_SOS = ("activa", "atendida", "cerrada")


class AlertaSOS(Base):
    __tablename__ = "alertas_sos"

    id = Column(Integer, primary_key=True, index=True)
    # quien disparo el SOS: 'conductor' o 'cliente'
    origen = Column(String(20), nullable=False)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False, index=True)
    viaje_id = Column(Integer, ForeignKey("viajes.id"), nullable=True, index=True)
    # datos de la persona que pide ayuda
    nombre_origen = Column(String(150), nullable=True)
    telefono_origen = Column(String(20), nullable=True)
    email_origen = Column(String(150), nullable=True)
    # si el SOS es de un conductor, guardamos su moto/seguro
    moto_descripcion = Column(String(200), nullable=True)
    seguro_descripcion = Column(String(200), nullable=True)
    # ubicacion al momento del SOS + la de la contraparte (viaje)
    ubicacion_lat = Column(Float, nullable=False)
    ubicacion_lng = Column(Float, nullable=False)
    contraparte_nombre = Column(String(150), nullable=True)
    contraparte_telefono = Column(String(20), nullable=True)
    contraparte_ubicacion_lat = Column(Float, nullable=True)
    contraparte_ubicacion_lng = Column(Float, nullable=True)
    estado = Column(String(20), nullable=False, server_default="activa", index=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
