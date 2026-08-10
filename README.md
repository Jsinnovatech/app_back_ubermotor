# UberMotor Backend

Backend FastAPI de **UberMotor** (moto-ride). Replica las prácticas de
**Comanda** (`app-back-comanda`): un solo login, perfiles 1:1, routers en
`api/v1/`, exceptions tipadas, `CustomException` global.

## Estructura

```
app/
├── main.py            # monta routers + exception handler global
├── database.py        # SQLAlchemy engine/session
├── core/              # config, security (JWT+roles), exceptions
├── models/            # usuarios + perfiles 1:1 + viajes/recargas/pagos
├── schemas/           # Pydantic
├── services/          # logica de negocio (saldo, viajes, admin)
└── api/v1/            # auth, conductores, clientes, viajes, recargas, admin
```

## Modelo de datos (3 perfiles)

Una tabla `usuarios` (login único) + perfiles 1:1: `conductores`, `clientes`,
`administradores` (super_admin / admin). Igual que Comanda.

## Regla de negocio (saldo prepago diario)

Implementada en `app/services/saldo_service.py`:

- Paquetes: 2 soles = 5 carreras | 4 soles = 10 carreras | 8 soles = 20 carreras.
- El saldo vale SOLO el día de la recarga (`saldo_fecha`) — no acumulable.
- Aceptar carrera → `saldo_carreras -= 1`.
- Cliente cancela → se devuelve la carrera.
- Conductor rechaza 3 → `-1` de saldo (`rechazos_hoy`).
- Saldo 0 → no acepta más carreras.
- Tarifa mínima 3 soles (validada en schema + service).

## Puesta en marcha

```bash
pip install -r requirements.txt
export DATABASE_URL=postgresql://...
python create_tables.py
uvicorn app.main:app --reload
```

## Análisis completo

`docs/analisis_modelo.md` — modelo de datos y decisiones de negocio.
