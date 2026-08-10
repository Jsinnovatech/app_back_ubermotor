# Análisis Backend — UberMoto

> **Estado:** borrador de diseño. Antes de escribir código, definimos el modelo de datos.
> Referencias de patrón: **Comanda** (super_admin/admin, validado en producción) y **Mercado Pago** (modelo tradicional de perfiles sobre una sola cuenta).

## 1. Objetivo

Sistema de moto-ride (tipo Uber de motos) con **un solo backend** y **tres perfiles de usuario**:

| Perfil | Rol | Qué hace |
|--------|-----|----------|
| **Conductor** | Presta el servicio | Ve pedidos, acepta, navega, cobra |
| **Cliente** | Consume el servicio | Pide un viaje, paga, califica |
| **Administrador** | Opera/controla | Gestión de usuarios, viajes, pagos, reportes |

Solo esos tres. Sin perfiles inventados: **esto ya es tradicional** (Mercado Pago usa el mismo esquema: una cuenta con roles).

## 2. Decisión clave: un solo login, perfiles encima

Igual que Comanda, **no** creamos una tabla de login por rol. Hay **una sola tabla `usuarios`** y cada perfil es una tabla `1:1` que extiende al usuario.

```
┌─────────────┐
│  usuarios   │  <- login único (email + password) + tipo_usuario
└──────┬──────┘
       │ 1:1
       ├──────────────┬───────────────┐
┌──────┴──────┐ ┌─────┴──────┐ ┌──────┴─────────┐
│ conductores │ │  clientes  │ │ administradores│
└─────────────┘ └────────────┘ └────────────────┘
```

**Por qué:**
- Un conductor también puede ser cliente (hacer que le traigan un repuesto).
- Un solo flujo de auth (registro/login/refresh/verificación), igual que Comanda.
- El `tipo_usuario` decide qué perfil se lee y qué pantalla ve el front (mismo patrón `_Portero` de Comanda).

## 3. Modelo de datos (v1)

### `usuarios` (tabla base)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| email | string unique | login |
| password_hash | string | bcrypt (mismo esquema que Comanda) |
| telefono | string | |
| tipo_usuario | enum | `conductor` \| `cliente` \| `administrador` |
| is_active | bool | |
| is_verified | bool | verificación de email/teléfono |
| refresh_token | string? | |
| created_at / updated_at | datetime | |

### `conductores` (1:1 con usuarios)

| Campo | Tipo | Notas |
|-------|------|-------|
| usuario_id | FK unique | |
| nombre | string | |
| dni | string | identificación |
| licencia | string | n° de licencia + categoría |
| foto_url | string? | |
| rating_promedio | decimal | calculado de calificaciones |
| viajes_completados | int | |
| disponible | bool | en línea / fuera de línea |
| ubicacion_lat / ubicacion_lng | decimal | posición en vivo |
| cuenta_pago | json? | datos bancarios/wallet para cobrar (revisar PII) |
| **saldo_carreras** | int | **saldo de carreras prepagadas (regla de negocio, ver §7)** |

### Vehículo (1:1 con conductor)

| Campo | Tipo | Notas |
|-------|------|-------|
| conductor_id | FK unique | |
| marca / modelo | string | |
| placa | string | |
| color | string | |
| soat_vencimiento | date | documento obligatorio |

### `clientes` (1:1 con usuarios)

| Campo | Tipo | Notas |
|-------|------|-------|
| usuario_id | FK unique | |
| nombre | string | |
| foto_url | string? | |
| rating_promedio | decimal | |
| viajes_realizados | int | |
| direcciones_favoritas | json? | lista de ubicaciones guardadas |

### `administradores` (1:1 con usuarios) — dos niveles

Igual que Comanda: **super_admin** (dueño de la plataforma) y **admin** (operador de una zona/empresa).

| Campo | Tipo | Notas |
|-------|------|-------|
| usuario_id | FK unique | |
| nombre | string | |
| nivel | enum | `super_admin` \| `admin` |
| zona_id | FK? | solo para `admin` (ciudad/región que opera) |
| recibe_notificaciones | bool | |

### `viajes` (núcleo del negocio)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| cliente_id | FK | |
| conductor_id | FK | nullable hasta que se asigna |
| estado | enum | `solicitado` \| `asignado` \| `en_curso` \| `completado` \| `cancelado` |
| cancelado_por | enum? | `cliente` \| `conductor` \| `admin` — **clave para la regla del saldo** |
| origen_lat/lng | decimal | |
| destino_lat/lng | decimal | |
| tarifa | decimal | **mínimo 3 soles (validado)** |
| metodo_pago_cliente | enum | `yape` \| `efectivo` — el cliente le paga directo al conductor |
| fecha | datetime | |

### `recargas` (prepago del conductor)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| conductor_id | FK | |
| paquete_id | FK | paquete comprado (2/4/8 soles) |
| monto | decimal | 2.00 / 4.00 / 8.00 |
| carreras | int | 5 / 10 / 20 |
| metodo | enum | `yape` \| `efectivo` \| `wallet` |
| estado | enum | `pendiente` \| `acreditado` \| `rechazado` |
| fecha | datetime | |

### `paquetes_carreras` (catálogo, editable por admin)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| nombre | string | ej. "Básico", "Clásico", "Pro" |
| monto | decimal | 2.00 / 4.00 / 8.00 |
| carreras | int | 5 / 10 / 20 |
| activo | bool | |

### `pagos` (referencia Mercado Pago)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| viaje_id | FK | |
| metodo | enum | `yape` \| `efectivo` \| `wallet` |
| monto | decimal | |
| estado | enum | `pendiente` \| `pagado` \| `reembolsado` |
| referencia_externa | string? | id de pago en Mercado Pago si se integra |

### `calificaciones`

| Campo | Tipo | Notas |
|-------|------|-------|
| viaje_id | FK unique | |
| autor | FK usuarios | quién califica |
| puntaje | int (1-5) | |
| comentario | string? | |

## 4. Roles y permisos (super_admin vs admin)

Misma filosofía que Comanda:

| Nivel | Puede |
|-------|-------|
| **super_admin** | Todo: usuarios, zonas, reportes globales, comisiones, gestión de admins, catálogo de paquetes |
| **admin** | Operar su **zona** (revisar viajes, aprobar conductores, reclamos, reportes de su zona) |

- El `tipo_usuario` se resuelve en el token JWT (como `role` en Comanda) y un dependency de FastAPI (`get_current_user` + check de rol) protege cada endpoint.
- Las pantallas del front se deciden por rol (patrón `_Portero` de Comanda).

## 5. Qué reutilizamos de Comanda

| Pieza | Cómo aplica acá |
|-------|------------------|
| `usuarios` + JWT + refresh + verificación | Base de auth idéntica |
| `es_admin` / `tipo_colaborador` | Se convierte en `tipo_usuario` + `nivel` |
| Rutas `app/api/v1/*` | `auth.py`, `viajes.py`, `conductores.py`, `clientes.py`, `admin.py`, `recargas.py` |
| `ApiClient` (front) | Se copia tal cual |
| Modelo de negocio: estados | `pendiente/listo/...` → `solicitado/asignado/en_curso/completado/cancelado` |

## 6. Referencia Mercado Pago (pagos)

Patrón tradicional que aplicamos:
- El **cliente** elige método de pago al pedir el viaje (Yape o efectivo).
- Si integramos MP para las **recargas del conductor**, guardamos `referencia_externa` y el estado se actualiza por webhook.
- La tabla `pagos`/`recargas` es la fuente única de verdad (sin estado calculado en memoria).

## 7. Regla de negocio: saldo de carreras (prepago) — el corazón del negocio

**Modelo:** el conductor **compra carreras por adelantado** (recarga). El **cliente le paga directo al conductor** (Yape o efectivo) con tarifa mínima de **3 soles por carrera**. La plataforma gana con el **prepago** del conductor, no con comisión del viaje.

### Paquetes (la "regla mágica": 10 carreras por 4 soles → 0.40 soles/carrera)

| Paquete | Precio | Carreras | Precio/carrera |
|---------|--------|---------:|----------------|
| Básico | 2 soles | 5 | 0.40 |
| Clásico | 4 soles | 10 | 0.40 |
| Pro | 8 soles | 20 | 0.40 |

> Precios pensados para ser **baratos y cómodos**; el catálogo vive en `paquetes_carreras` y el admin lo puede editar sin tocar código.

### Validaciones de la regla (sin agujeros)

1. **Aceptar una carrera** → `conductores.saldo_carreras -= 1`.
2. **El cliente cancela** → la carrera **se devuelve al saldo** (`saldo_carreras += 1`). No se pierde.
3. **El conductor cancela** → la carrera **NO se devuelve** (evita abuso: nadie toma una carrera y la bota sin costo).
4. `saldo_carreras == 0` → el conductor **no puede aceptar más carreras** hasta recargar. El front le avisa ("te quedan 2 carreras") y bloquea la aceptación.
5. **Tarifa mínima 3 soles** → validada al crear el viaje (el cliente paga al conductor en Yape/efectivo).
6. La recarga **solo se acredita cuando el pago se confirma** (estado `acreditado`).

### Flujo típico

```
1. Conductor recarga 4 soles (Yape) → paquete Clásico → saldo = 10
2. Cliente pide un viaje, el conductor acepta → saldo = 9
3. Viaje completado → el cliente le paga al conductor (Yape/efectivo, mínimo 3 soles)
4. Cliente cancela a mitad → saldo vuelve a 10 (carrera devuelta)
5. Saldo llega a 0 → el conductor recarga para seguir aceptando carreras
```

## 8. API inicial sugerida (`app/api/v1/`)

- `auth/` → registro, login, refresh, verificación (por perfil)
- `conductores/` → perfil, disponibilidad, ubicación, **saldo_carreras**, aprobación (admin)
- `recargas/` → listar paquetes, comprar paquete, confirmar pago, historial
- `clientes/` → perfil, direcciones
- `viajes/` → solicitar, asignar, estado, cancelar (con `cancelado_por`), historial
- `pagos/` → crear, confirmar, historial
- `admin/` → usuarios, zonas, reportes, aprobaciones, **catálogo de paquetes**

## 9. Decisiones pendientes

- [x] **Regla de negocio:** prepago por saldo de carreras (2/4/8 soles → 5/10/20 carreras). **Confirmado.**
- [x] **Cancelación del cliente** → se devuelve la carrera. **Confirmado.**
- [ ] ¿El conductor cancela pierde la carrera siempre, o con tope de "X cancela al día"?
- [ ] ¿Integrar Mercado Pago para la recarga desde la v1 o solo Yape manual + validación por admin?
- [ ] ¿PII de cuenta bancaria del conductor: cifrarla o delegarla a MP?
- [ ] Definir umbrales de rating (bloqueo automático de conductores).
- [ ] ¿`zona_id` por admin desde la v1 o global al inicio?

## 10. Siguiente paso sugerido

1. Aprobar este modelo (3 perfiles + regla de saldo).
2. Crear la estructura FastAPI (misma que Comanda: `app/models`, `app/schemas`, `app/api/v1`, `app/services`).
3. Migraciones + tablas base (incluyendo `paquetes_carreras` y `recargas`).
4. Flujo de auth por perfil + `_Portero` del front.
