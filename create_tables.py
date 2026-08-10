# Crea todas las tablas del esquema de UberMotor.
# Uso: python create_tables.py
from app.database import Base, engine
from app import models  # noqa: F401  (registra los modelos en Base.metadata)

print("Creando tablas de UberMotor...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas")
