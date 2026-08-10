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
| origen_lat/lng | decimal | |
| destino_lat/lng | decimal | |
| tarifa | decimal | calculada al aceptar |
| fecha | datetime | |

### `pagos` (referencia Mercado Pago)

| Campo | Tipo | Notas |
|-------|------|-------|
| id | PK | |
| viaje_id | FK | |
| metodo | enum | `efectivo` \| `tarjeta` \| `wallet` |
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
| **super_admin** | Todo: usuarios, zonas, reportes globales, comisiones, gestión de admins |
| **admin** | Operar su **zona** (revisar viajes, aprobar conductores, reclamos, reportes de su zona) |

- El `tipo_usuario` se resuelve en el token JWT (como `role` en Comanda) y un dependency de FastAPI (`get_current_user` + check de rol) protege cada endpoint.
- Las pantallas del front se deciden por rol (patrón `_Portero` de Comanda).

## 5. Qué reutilizamos de Comanda

| Pieza | Cómo aplica acá |
|-------|------------------|
| `usuarios` + JWT + refresh + verificación | Base de auth idéntica |
| `es_admin` / `tipo_colaborador` | Se convierte en `tipo_usuario` + `nivel` |
| Rutas `app/api/v1/*` | `auth.py`, `viajes.py`, `conductores.py`, `clientes.py`, `admin.py` |
| `ApiClient` (front) | Se copia tal cual |
| Modelo de negocio: estados | `pendiente/listo/...` → `solicitado/asignado/en_curso/completado/cancelado` |

## 6. Referencia Mercado Pago (pagos)

Patrón tradicional que aplicamos:
- El **cliente** elige método de pago al pedir el viaje (efectivo, tarjeta, wallet).
- Si integramos MP, guardamos `referencia_externa` y el estado se actualiza por webhook.
- El **conductor** cobra a fin de día: comisión de la plataforma → pago a su cuenta.
- La tabla `pagos` es la fuente única de verdad (sin estado calculado en memoria).

## 7. API inicial sugerida (`app/api/v1/`)

- `auth/` → registro, login, refresh, verificación (por perfil)
- `conductores/` → perfil, disponibilidad, ubicación, aprobación (admin)
- `clientes/` → perfil, direcciones
- `viajes/` → solicitar, asignar, estado, cancelar, historial
- `pagos/` → crear, confirmar, historial
- `admin/` → usuarios, zonas, reportes, aprobaciones

## 8. Decisiones pendientes

- [ ] ¿`zona_id` por admin desde la v1 o global al inicio?
- [ ] ¿Integrar Mercado Pago desde la v1 o solo efectivo + wallet interna?
- [ ] ¿Separar `conductores`/`clientes`/`administradores` en tablas (propuesto) o todo en `usuarios` con campos nullable?
- [ ] ¿PII de cuenta bancaria del conductor: cifrarla o delegarla a MP?
- [ ] Definir umbrales de rating (bloqueo automático de conductores).

## 9. Siguiente paso sugerido

1. Aprobar este modelo (3 perfiles).
2. Crear la estructura FastAPI (misma que Comanda: `app/models`, `app/schemas`, `app/api/v1`, `app/services`).
3. Migraciones + tablas base.
4. Flujo de auth por perfil + `_Portero` del front.
