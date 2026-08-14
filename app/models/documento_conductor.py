from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, func

from app.database import Base

# Tipos de documento que el conductor debe subir para su validacion.
# El admin revisa cada uno antes de aprobarlo.
TIPOS_DOCUMENTO = ("dni", "brevete", "soat", "moto")
CARAS_DOCUMENTO = ("frente", "dorso")


class DocumentoConductor(Base):
    __tablename__ = "documentos_conductores"

    id = Column(Integer, primary_key=True, index=True)
    conductor_id = Column(Integer, ForeignKey("conductores.id"), nullable=False, index=True)
    # tipo: dni | brevete | soat | moto
    tipo = Column(String(20), nullable=False)
    # cara: frente | dorso (None para soat/moto que son una sola foto)
    cara = Column(String(10), nullable=True)
    url = Column(String(500), nullable=False)

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
