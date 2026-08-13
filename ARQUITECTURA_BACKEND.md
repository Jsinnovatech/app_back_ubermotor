# Arquitectura del Backend — HablaVas

> Mototaxi ride-hailing estilo InDrive: el cliente ofrece tarifa, el conductor decide si la toma. Pago directo al conductor (Yape/efectivo); la plataforma gana con el **prepago de carreras** del conductor.

## Stack

| Componente | Tecnología |
|---|---|
| Framework | FastAPI 0.115 (Python 3.12) |
| ORM | SQLAlchemy 2.0 |
| BD | PostgreSQL (Railway) |
| Auth | JWT (python-jose) + bcrypt |
| Validación | Pydantic 2 |
| Realtime | WebSocket nativo de FastAPI |
| Storage | ImageKit (fotos, documentos) |
| Email | Resend (recuperación de contraseña) |
| Deploy | Nixpacks + uvicorn en Railway |

---

## Estructura por capas

```
app/
├── main.py                    # App FastAPI: monta routers, CORS, handlers de error
├── database.py                # Motor SQLAlchemy, Session, Base
├── api/
│   └── v1/                    # ROUTERS (capa HTTP, delgados: validan rol y delegan)
│       ├── auth.py            # /auth  (registro, login, reset de password)
│       ├── conductores.py     # /api/v1/conductores
│       ├── clientes.py        # /api/v1/clientes
│       ├── viajes.py          # /api/v1/viajes
│       ├── recargas.py        # /api/v1/recargas
│       ├── admin.py           # /api/v1/admin
│       ├── sos.py             # /api/v1/sos
│       ├── autoridades.py     # /api/v1/autoridades (Serenazgo/Policía)
│       ├── calificaciones.py  # /api/v1/calificaciones
│       └── realtime.py        # WebSockets /ws/conductores, /ws/clientes
├── services/                  # SERVICES (toda la regla de negocio)
│   ├── auth_service.py
│   ├── conductor_service.py
│   ├── viaje_service.py       # ciclo de vida del viaje + serializadores
│   ├── saldo_service.py       # prepago diario, recargas, rechazos
│   ├── calificacion_service.py
│   ├── sos_service.py         # alertas + webhook a Policía
│   ├── realtime_service.py    # conexiones WS en memoria
│   ├── email_service.py       # Resend
│   └── storage/imagekit_service.py
├── models/                    # ORM (tablas)
├── schemas/                   # Pydantic (entrada/salida)
└── core/
    ├── config.py              # Settings (variables de entorno)
    ├── security.py            # JWT, hashing, requiere_tipo
    └── exceptions.py          # NotFoundException, ValidationException, etc.
```

**Regla de oro:** los routers **no** hacen queries ni `db.commit()` ni asignan campos — solo resuelven el perfil del usuario autenticado y delegan en el service. Toda la lógica de negocio vive en `services/`.

---

## Modelo de datos

### Usuarios y perfiles (1:1)

```
usuarios (email, password_hash, telefono, tipo_usuario, activo)
   ├── conductores   (nombre, DNI, licencia, fotos, rating, disponible, saldo_carreras, saldo_fecha)
   │     └── vehiculos (marca, modelo, placa, color, foto, SOAT)
   ├── clientes      (nombre, foto_url, rating, viajes_realizados, direcciones_favoritas)
   └── administradores (nivel: admin | super_admin)
```

`tipo_usuario` puede ser: `conductor | cliente | administrador | serenazgo | policia`.

- Conductor, cliente y administrador tienen perfil 1:1 en su tabla.
- **Serenazgo/Policía** no tienen perfil propio: el nombre vive en `usuarios`, el rol decide qué pantalla ven.

### Viajes

`viajes` (cliente_id, conductor_id, estado, origen/destino lat-lng + direcciones, tarifa, metodo_pago_cliente)

```
ESTADOS_VIAJE = ("solicitado", "asignado", "llegado", "en_curso", "completado", "cancelado", "rechazado")
```

| Estado | Significado |
|---|---|
| `solicitado` | El cliente pidió; está en la cola de conductores |
| `asignado` | El conductor aceptó y consume 1 carrera de su saldo |
| `llegado` | El conductor puso "Llegué" al punto de recogida |
| `en_curso` | El conductor inició el viaje (cliente subió) |
| `completado` | Llegó al destino; suma viaje completado e ingreso |
| `cancelado` | Cancelado (cliente → se devuelve saldo; conductor → cuenta como rechazo) |
| `rechazado` | El conductor rechazó; alimenta el contador de rechazos |

### Otras tablas

- `paquetes_carreras` — paquetes prepago: **2 = 5**, **4 = 10**, **8 = 20** (0.40/carrera)
- `recargas` — compra del paquete (pendiente → acreditado)
- `calificaciones` — mutua (conductor↔cliente), 1-5 estrellas
- `alertas_sos` — botón SOS con datos de origen/contraparte/moto
- `pagos` — pagos registrados

---

## Regla de negocio del saldo (prepago diario)

Central en `saldo_service.py`:

1. **El conductor compra carreras por adelantado** (recarga de un paquete).
2. El saldo vale **solo el día** de la recarga: `saldo_fecha`. Al llegar un día nuevo, se reporta 0.
3. **Aceptar una carrera** → `saldo -= 1`. Con saldo 0 no puede aceptar.
4. **Cliente cancela** → la carrera se devuelve al saldo (`saldo += 1`).
5. **Cada 3 rechazos** del conductor → `saldo -= 1` (mínimo 0).
6. Tarifa mínima por carrera: **S/ 3.00** (`TARIFA_MINIMA_CARRERA`).

---

## Autenticación y autorización

- JWT con `tipo_usuario` embebido. Token de **12 horas** (`ACCESS_TOKEN_EXPIRE_MINUTES`).
- `SecurityService.hash_password` / `verify_password` (bcrypt).
- `requiere_tipo("conductor", "cliente", ...)` → dependencia factory que valida el rol en cada endpoint.
- `get_usuario_actual` → resuelve `UsuarioActual(usuario_id, tipo_usuario)` desde el Bearer token.
- **Recuperación de contraseña**: `POST /auth/solicitar-reset` envía un código de 6 dígitos por email (Resend, 15 min de vigencia) y `POST /auth/resetear-password` lo valida y cambia la contraseña.

---

## Realtime (WebSockets)

`realtime_service.py` mantiene **en memoria** las conexiones por rol:

| Canal | Quién | Recibe |
|---|---|---|
| `/ws/conductores` | Conductor | `viaje_nuevo` (carreras empujadas al instante, patrón InDrive) |
| `/ws/clientes` | Cliente | `ubicacion_conductor` (posición en vivo del conductor de su viaje) |

- Autenticación por `?token=` en la URL (los WebSocket de Flutter web no envían headers de forma fiable).
- El **polling de 5s** queda como fallback si el WS cae.
- Cuando el conductor actualiza su ubicación (`PUT /conductores/ubicacion`) y tiene un viaje activo, el backend empuja la posición al cliente conectado.

---

## SOS / Serenazgo / Policía

1. `POST /api/v1/sos` — conductor o cliente dispara la alerta (doble toque en el front).
2. Se registra la alerta con: origen (conductor/cliente), ubicación, foto, moto, seguro, contraparte.
3. Se dispara un **webhook externo** a `POLICIA_WEBHOOK_URL` (con Basic Auth opcional `POLICIA_WEBHOOK_USUARIO`/`POLICIA_WEBHOOK_CLAVE`).
4. `GET /api/v1/autoridades/alertas` — Serenazgo/Policía ven las alertas activas.
5. `GET /alertas/{id}/ubicacion-vivo` — posición actual del conductor para seguir la moto en el mapa.
6. `POST /api/v1/sos/{id}/cerrar` — marcar como atendida.

---

## Calificaciones

- `POST /calificaciones` — mutua: conductor califica al rider y cliente califica al conductor (1-5).
- `GET /calificaciones/ranking` — ranking de conductores por rating promedio.
- `rating_promedio` y `viajes_completados`/`viajes_realizados` se actualizan en los perfiles.

---

## Variables de entorno (Railway)

| Variable | Descripción |
|---|---|
| `DATABASE_URL` | Conexión PostgreSQL |
| `SECRET_KEY` | Firma de JWT |
| `CORS_ORIGINS` | Lista separada por comas de orígenes permitidos (nunca `*` con credentials) |
| `IMAGEKIT_PUBLIC_KEY` / `PRIVATE_KEY` / `URL_ENDPOINT` | Storage de imágenes |
| `RESEND_API_KEY` | Emails (recuperación de contraseña) |
| `EMAIL_FROM_ADDRESS` / `EMAIL_FROM_NAME` | Remitente de los emails |
| `POLICIA_WEBHOOK_URL` | Endpoint externo del sistema policial |
| `POLICIA_WEBHOOK_USUARIO` / `POLICIA_WEBHOOK_CLAVE` | Credenciales Basic Auth del webhook |

Valores por defecto en `app/core/config.py` (`Settings`).

---

## Ciclo de vida de una carrera (end-to-end)

```
CLIENTE                     BACKEND                          CONDUCTOR
   │  POST /clientes/viajes   │                                  │
   ├─────────────────────────►│  estado = solicitado             │
   │                          │  WS empuja viaje_nuevo ─────────►│  Panel "Nueva carrera"
   │                          │  ◄───────── POST /viajes/{id}/aceptar
   │  "Conductor en camino"   │  estado = asignado, saldo -= 1   │
   │  ◄────────────────────────── WS ubicacion (tracking)         │
   │                          │  POST /viajes/{id}/llegar        │  botón "Llegué"
   │  "Tu conductor llegó"    │  estado = llegado                │
   │                          │  POST /viajes/{id}/iniciar       │  botón "Iniciar viaje"
   │  "En viaje" (pin se mueve)│ estado = en_curso               │
   │                          │  POST /viajes/{id}/completar     │  botón "Completar"
   │  "Califica a tu conductor"│ estado = completado             │
   │  POST /calificaciones    │  viajes_completados += 1         │
```

**Regla de 1 carrera activa:** un conductor no puede aceptar otra carrera mientras tenga una en `asignado`, `llegado` o `en_curso`.

---

## Endpoints principales

| Método | Ruta | Rol | Propósito |
|---|---|---|---|
| POST | `/auth/registro` | público | Crear cuenta (tipo decide perfil) |
| POST | `/auth/login` | público | Login |
| POST | `/auth/solicitar-reset` / `resetear-password` | público | Recuperar contraseña |
| GET | `/api/v1/viajes/disponibles` | conductor | Carreras `solicitado` en el radio (con rider) |
| POST | `/api/v1/viajes/{id}/aceptar` | conductor | Aceptar (consume saldo, valida 1 activa) |
| POST | `/api/v1/viajes/{id}/rechazar` | conductor | Rechazar (cuenta para -1/3) |
| POST | `/api/v1/viajes/{id}/llegar` | conductor | Marcar llegada al punto |
| POST | `/api/v1/viajes/{id}/iniciar` | conductor | Iniciar viaje |
| POST | `/api/v1/viajes/{id}/completar` | conductor | Completar |
| POST | `/api/v1/viajes/{id}/cancelar` | cliente/conductor | Cancelar (regla de saldo) |
| GET | `/api/v1/conductores/viaje-activo` | conductor | Carrera en curso del conductor |
| GET | `/api/v1/clientes/viaje-activo` | cliente | Carrera en curso del cliente (con datos del conductor) |
| POST | `/api/v1/clientes/viajes` | cliente | Pedir viaje |
| GET | `/api/v1/conductores/perfil` | conductor | Perfil + saldo vigente + ingreso del día |
| GET | `/api/v1/clientes/perfil` | cliente | Perfil (nombre, foto, viajes, rating) |
| POST | `/api/v1/conductores/documentos` | conductor | Subir foto/DNI/licencia/antecedentes/moto |
| POST | `/api/v1/clientes/foto` | cliente | Subir foto de perfil |
| GET/POST | `/api/v1/recargas/...` | conductor | Paquetes, comprar, confirmar |
| POST | `/api/v1/sos` | conductor/cliente | Activar alerta SOS |
| GET | `/api/v1/autoridades/alertas` | policía/serenazgo | Central SOS |
| POST | `/api/v1/calificaciones` | ambos | Calificar viaje |

---

## Despliegue (Railway)

- **Nixpacks** detecta Python + `requirements.txt`.
- `railway.toml`:
  ```toml
  [build]
  builder = "NIXPACKS"

  [deploy]
  startCommand = "uvicorn app.main:app --host 0.0.0.0 --port $PORT"
  ```
- URL producción: `https://appbackubermotor-production.up.railway.app`
- Redeploy (MCP Railway): `serviceInstanceRedeploy` sobre el servicio backend.
