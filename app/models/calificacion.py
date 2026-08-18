from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint, func

from app.database import Base


class Calificacion(Base):
    __tablename__ = "calificaciones"
    __table_args__ = (
        # Calificacion MUTUA: cada lado (cliente y conductor) califica una vez
        # por viaje, con su comentario.
        UniqueConstraint("viaje_id", "autor_id", name="uq_calificacion_viaje_autor"),
    )

    id = Column(Integer, primary_key=True, index=True)
    viaje_id = Column(Integer, ForeignKey("viajes.id"), nullable=False, index=True)
    autor_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)
    puntaje = Column(Integer, nullable=False)  # 1-5
    comentario = Column(String(300), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
