# Crea todas las tablas del esquema de UberMotor y siembra los paquetes
# de la regla de negocio (2 soles = 5 carreras, 4 = 10, 8 = 20).
# Uso: DATABASE_URL=postgresql://... python create_tables.py
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.database import Base, engine
from app import models  # noqa: F401  (registra los modelos en Base.metadata)

print("Creando tablas de UberMotor...")
Base.metadata.create_all(bind=engine)
print("✅ Tablas creadas")

# Seed de paquetes (regla magica: 10 carreras por 4 soles -> 0.40/carrera)
PAQUETES = [
    ("Basico", 2, 5),
    ("Clasico", 4, 10),
    ("Pro", 8, 20),
]

with Session(engine) as db:
    for nombre, monto, carreras in PAQUETES:
        existe = db.execute(
            text("SELECT 1 FROM paquetes_carreras WHERE monto = :monto AND carreras = :carreras"),
            {"monto": monto, "carreras": carreras},
        ).first()
        if not existe:
            db.execute(
                text(
                    "INSERT INTO paquetes_carreras (nombre, monto, carreras, activo) "
                    "VALUES (:nombre, :monto, :carreras, true)"
                ),
                {"nombre": nombre, "monto": monto, "carreras": carreras},
            )
            print(f"  + paquete {nombre} (S/ {monto} -> {carreras} carreras)")
    db.commit()

print("✅ Seed de paquetes listo (2/4/8 soles)")
