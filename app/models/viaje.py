# Núcleo del negocio: un viaje entre un cliente y un conductor.
# El estado 'rechazado' alimenta el contador de rechazos del conductor
# (cada 3 rechazos se descuenta 1 carrera del saldo).
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, func

from app.database import Base

ESTADOS_VIAJE = ("solicitado", "asignado", "llegado", "en_curso", "completado", "cancelado", "rechazado")
CANCELADO_POR = ("cliente", "conductor", "admin")


class Viaje(Base):
    __tablename__ = "viajes"

    id = Column(Integer, primary_key=True, index=True)
    cliente_id = Column(Integer, ForeignKey("clientes.id"), nullable=False, index=True)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=True, index=True)
    estado = Column(String(20), nullable=False, server_default="solicitado", index=True)
    cancelado_por = Column(String(20), nullable=True)

    origen_lat = Column(Float, nullable=False)
    origen_lng = Column(Float, nullable=False)
    destino_lat = Column(Float, nullable=False)
    destino_lng = Column(Float, nullable=False)
    origen_direccion = Column(String(200), nullable=True)
    destino_direccion = Column(String(200), nullable=True)

    # Tarifa minima validada en el service: settings.TARIFA_MINIMA_CARRERA (3 soles).
    tarifa = Column(Float, nullable=False)
    # El cliente le paga directo al conductor (Yape o efectivo), la plataforma
    # no cobra comision: gana con el prepago del saldo.
    metodo_pago_cliente = Column(String(20), nullable=False, server_default="yape")

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
