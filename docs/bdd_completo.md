# BDD Completo — HablaVas

> Documento de comportamiento (Behavior-Driven Development) del sistema completo.
> Cada caso describe: actor, precondición, acción que se puede **clickear**, y
> resultado esperado. Nada queda suelto: todo flujo termina en algo visible.

---

## 1. Actores del sistema

| Actor | Login | Pantalla principal | Qué ve |
|-------|-------|--------------------|--------|
| **Conductor** | email+password (rol conductor) | Home conductor | Mapa de carreras cercanas, saldo, recargar, perfil, SOS |
| **Cliente** | email+password (rol cliente) | Home cliente | Motos disponibles cerca, pedir viaje, SOS |
| **Admin** | email+password (rol administrador) | Shell admin | Dashboard, paquetes, aprobar conductores |
| **Serenazgo** | email+password (rol serenazgo) | Central SOS | Alertas SOS activas con mapa en vivo |
| **Policía** | email+password (rol policia) | Central SOS | Alertas SOS activas con mapa en vivo |

---

## 2. Flujo de registro y login

### 2.1 Registro de usuario (todos los roles)
- **Actor:** cualquier persona
- **Click:** "No tengo cuenta — Registrarme"
- **Click:** elegir rol en el segmented control (Conductor / Cliente / Admin / Policía)
- **Click:** completar nombre, email, contraseña → "Registrarme"
- **Resultado:** queda logueado y ve la pantalla de su rol.

### 2.2 Login
- **Click:** email + contraseña → "Ingresar"
- **Resultado:** el `_Portero` lo manda a la pantalla de su rol según `tipo_usuario`.

---

## 3. Conductor

### 3.1 Home conductor
- **Click:** toggle "En línea/Offline" → cambia `disponible` en el backend; si está en línea, recibe carreras.
- **Ve:** "Te quedan N carreras" (saldo del día), "Balance de Hoy", mapa con pines de carreras cercanas (radio 5km).

### 3.2 Ver carreras en el mapa
- **Precondición:** estar en línea, aprobado, con saldo > 0.
- **Ve:** pines verdes (origen) y negros (destino) de las carreras **de su zona** (filtro Haversine por lat/lng del GPS).
- **Resultado:** cada 5s se refresca la ubicación y las carreras (polling fallback) + WebSocket empuja carreras nuevas al instante.

### 3.3 Tomar una carrera
- **Click:** pin del mapa → diálogo "Carrera disponible" con origen/destino/tarifa.
- **Click:** "Aceptar" → saldo baja 1 → la carrera sale del mapa y pasa a "asignado".
- **Click:** "Rechazar" (en lista) → cuenta para la regla: **cada 3 rechazos → -1 saldo**.

### 3.4 Recargar saldo (prepago diario)
- **Click:** botón "Recargar carreras" → pantalla Recarga.
- **Click:** elegir paquete **Básico S/2 = 5 | Clásico S/4 = 10 | Pro S/8 = 20** (el de 10 sale "Recomendado").
- **Click:** "Pagar con Yape" → modal "¡Recarga Exitosa!" con saldo actual y "Vencimiento Hoy 23:59".
- **Regla:** el saldo vale **solo ese día** (no acumulable); al aceptar se descuenta; si el **cliente cancela** se devuelve.

### 3.5 Subir documentos (onboarding)
- **Click:** "Account" (bottom nav) → Perfil.
- **Click:** "Subir" en cada documento: Tu foto, DNI, Licencia, Antecedentes.
- **Resultado:** se sube a ImageKit, aparece "Subido ✓". El admin los revisa para aprobar (`aprobado`).
- **Click:** "Cerrar sesión".

### 3.6 Historial (Rides)
- **Click:** "Rides" (bottom nav) → historial de viajes con estado y tarifa.

### 3.7 SOS (emergencia)
- **Precondición:** cualquier momento.
- **Click:** botón SOS rojo **1ª vez** → se arma "¿SOS?".
- **Click:** **2ª vez** (dentro de 3s) → alerta enviada a Serenazgo/Policía con sus datos + ubicación + webhook.

---

## 4. Cliente

### 4.1 Ver motos disponibles
- **Precondición:** logueado como cliente.
- **Ve:** "Motos disponibles cerca (N)" — conductores aprobados + en línea + con saldo, ordenados por distancia.

### 4.2 Ver reputación del conductor
- **Click:** tarjeta de una moto → bottom sheet con **rating, viajes, distancia, moto (marca/modelo/placa)**.

### 4.3 Pedir un viaje
- **Click:** destino → tarifa (mínima **S/ 3.00**, stepper -/+) → Efectivo o Yape.
- **Click:** "Pedir viaje" → "Viaje solicitado. Un conductor pronto lo tomará."
- **Resultado:** el viaje aparece en los conductores de la zona por WebSocket.

### 4.4 SOS
- **Click:** botón SOS rojo ×2 → alerta con sus datos + datos del chofer del viaje activo + ubicación.

---

## 5. Calificación y ranking

### 5.1 Calificar un viaje
- **Precondición:** viaje **completado**.
- **Acción:** el cliente (o el conductor) califica **1-5 estrellas** (opcional comentario).
- **Validaciones (backend):** solo viajes completados; solo el cliente o conductor de ese viaje; una sola calificación por viaje.
- **Resultado:** si califica el cliente → se **recalcula el rating_promedio del conductor**.

### 5.2 Ranking de conductores
- **Endpoint:** `GET /api/v1/calificaciones/ranking` → conductores ordenados por rating (desempate por viajes completados).

---

## 6. Administrador

### 6.1 Dashboard
- **Ve:** métricas (conductores activos, viajes, recaudación, carreras vendidas).

### 6.2 Gestión de paquetes
- **Click:** tab "Paquetes" → ve el catálogo (2/5, 4/10, 8/20).
- **Resultado:** (super_admin) puede crear/editar/desactivar paquetes.

### 6.3 Aprobar conductores
- **Endpoint:** `POST /api/v1/admin/conductores/{id}/aprobar`.
- **Resultado:** el conductor aparece disponible para los clientes solo si `aprobado=true`.

---

## 7. Serenazgo / Policía

### 7.1 Central SOS
- **Precondición:** logueado como serenazgo o policia.
- **Ve:** alertas SOS activas con: nombre, teléfono, moto, seguro, contraparte.
- **Mapa en tiempo real:** pin rojo (SOS) + pin azul (contraparte si viaja), refresca cada 5s.
- **Click:** "Marcar como atendida" → la alerta sale de la lista.

---

## 8. Reglas de negocio transversales (no clickeables, se validan en el backend)

| Regla | Comportamiento |
|-------|----------------|
| **Tarifa mínima** | No se puede pedir viaje con tarifa < S/ 3.00 (schema + service). |
| **Saldo diario** | El saldo vale solo el día de la recarga (`saldo_fecha`); si es otro día se reporta 0. |
| **Rechazos** | Cada 3 rechazos del conductor → -1 carrera de saldo. |
| **Devolución** | Si el cliente cancela la carrera aceptada → se devuelve al saldo. |
| **Saldo 0** | Conductor sin saldo no puede aceptar carreras (ni aparece para el cliente). |
| **Cercanía** | El conductor solo ve carreras cuyo origen esté dentro del radio (5km). |
| **SOS** | Requiere 2 presiones para activar (anti falso positivo). |
| **Calificación** | Solo viajes completados, solo los involucrados, 1 por viaje. |

---

## 9. Mapa de endpoints (para verificar qué existe de verdad)

### Auth
- `POST /auth/registro` · `POST /auth/login` · `GET /auth/me`

### Conductor
- `GET/PUT /api/v1/conductores/perfil` · `PUT .../disponibilidad` · `PUT .../ubicacion` · `GET .../saldo` · `GET .../paquetes` · `POST .../recargar` · `GET .../historial` · `POST .../documentos`

### Cliente
- `GET /api/v1/clientes/conductores-disponibles?lat&lng` · `POST/GET /api/v1/clientes/viajes`

### Viajes
- `GET /api/v1/viajes/disponibles?lat&lng&radio_km` · `POST .../{id}/aceptar|rechazar|iniciar|completar|cancelar`

### Recargas
- `GET /api/v1/recargas/paquetes` · `POST .../comprar` · `POST .../{id}/confirmar`

### Calificaciones
- `POST /api/v1/calificaciones` · `GET /api/v1/calificaciones/ranking`

### SOS y Autoridades
- `POST /api/v1/sos` · `POST /api/v1/sos/{id}/cerrar` · `GET /api/v1/autoridades/alertas`

### Admin
- `GET /api/v1/admin/conductores` · `POST .../{id}/aprobar` · `GET/POST /api/v1/admin/paquetes` · `PUT .../{id}` · `GET .../viajes` · `GET .../recargas`

### Realtime
- `WS /ws/conductores?token=...` (push de carreras nuevas)

---

## 10. Estado real (verificado)

- ✅ Implementado y compilado: todos los flujos de los puntos 2-7.
- ✅ Calificación + ranking: endpoint y service creados (patrón Comanda).
- 🔜 Pendiente de UI: pantalla de **calificar viaje** en el front (el endpoint ya existe) y pantalla de **ranking**.
