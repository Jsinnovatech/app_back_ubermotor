# Notificaciones Push (OneSignal) — HablaVas/UberMoto

## Por qué

El WebSocket (`realtime_manager`) solo entrega eventos con la app **abierta**. Para que el celular suene/vibre con la app cerrada o en segundo plano (ej. "te llegó una carrera" al conductor mientras tiene la pantalla apagada), hace falta push real vía Firebase Cloud Messaging (FCM). OneSignal es la capa que envuelve FCM para no tener que manejar tokens de dispositivo a mano.

## Arquitectura

```
Backend (FastAPI)              OneSignal                    Celular (Flutter)
─────────────────              ─────────                    ─────────────────
push_service.enviar()  ──POST──▶ api.onesignal.com  ──FCM──▶ OneSignal SDK (Android)
  include_external_user_ids                                    │
  = "conductor_{id}" /                                          ▼
    "cliente_{id}"                                        Notificación nativa
```

- **Backend → OneSignal**: un solo `POST /notifications` con `include_external_user_ids`, sin tocar Firebase directo. Auth: `Authorization: Basic {ONESIGNAL_REST_API_KEY}`.
- **OneSignal → celular**: OneSignal decide a qué token FCM real mandarlo, usando su propio mapeo interno (external_id ↔ token del dispositivo).
- **App → OneSignal (registro)**: al hacer login, el front llama `OneSignal.login(externalId)` con `conductor_{usuario_id}` o `cliente_{usuario_id}` — así el backend nunca necesita saber el token FCM real de cada teléfono, solo el ID de negocio (`usuario_id`).

## Cuándo se dispara cada notificación

| Evento | Trigger (dónde en el código) | Quién la recibe | Mensaje |
|---|---|---|---|
| `viaje_nuevo` | `clientes.py:67` — cliente crea una solicitud de viaje | Conductores **cercanos, aprobados, disponibles, con saldo** (`conductores_disponibles_cerca`) | "Nueva carrera disponible — Cliente en {origen} · S/ {tarifa}" |
| `viaje_aceptado` | `viajes.py:81` — conductor acepta la carrera | El cliente que pidió el viaje | "🚴 Conductor en camino — {nombre} ({moto} {placa}) está en camino" |
| `viaje_llegado` | `viajes.py:119` — conductor marca que llegó al punto de recojo | El cliente | "Tu conductor llegó" |
| `viaje_completado` | `viajes.py:134` — se cierra el viaje | El cliente | "Viaje completado — Carrera finalizada (S/ {tarifa})" |
| `viaje_cancelado` | `viajes.py:158` — cliente cancela una carrera ya asignada | El conductor que tenía la carrera | "Carrera cancelada — La oferta vuelve a estar disponible" |

Todas van con `data.tipo` (`viaje_nuevo`, `viaje_aceptado`, etc.) + `data.viaje_id`, para que el front pueda reaccionar al tocar la notificación (`PushService._abrirPantallaPorPush` en el front hoy solo vuelve al Home; se puede extender a navegar directo al viaje usando ese `data`).

`push_service._habilitado` es `False` si faltan `ONESIGNAL_APP_ID` u `ONESIGNAL_REST_API_KEY` en el backend — en ese caso todas las funciones `notificar_*` son no-op silencioso (no rompen el flujo de negocio si el push no está configurado).

## Configuración requerida

### Backend (`app/core/config.py`, variables de entorno)
- `ONESIGNAL_APP_ID` — App ID de OneSignal (`0adcd75f-49c3-43ac-9003-489259beac95`)
- `ONESIGNAL_REST_API_KEY` — REST API Key de OneSignal (Settings → Keys & IDs)

### Front (Flutter)
- `pubspec.yaml`: `onesignal_flutter: 5.5.2` (pin exacto — requiere Activity tipo `FragmentActivity`)
- `lib/core/config/api_config.dart`: `onesignalAppId` — mismo App ID que el backend, embebido como default o via `--dart-define=ONESIGNAL_APP_ID=...`
- `lib/services/onesignal_service.dart` (`PushService`): inicializa el SDK, muestra el diálogo de verificación estándar de OneSignal, y vincula/desvincula el `external_id` en login/logout

### Nativo Android (obligatorio, no solo Dart)
1. `android/app/src/main/kotlin/.../MainActivity.kt`: la Activity debe extender **`FlutterFragmentActivity`** (no `FlutterActivity`) — OneSignal v5 registra su plugin nativo automáticamente al arrancar la app (pase lo que pase en Dart) e intenta usar un `Fragment`; con `FlutterActivity` normal eso es un `ClassCastException` nativo que cierra la app **antes** de que Flutter tenga control.
2. `android/app/build.gradle.kts` + `android/settings.gradle.kts`: plugin `com.google.gms.google-services` (versión 4.4.2)
3. `android/app/google-services.json`: descargado de Firebase Console (proyecto `app-hablavas`) — necesario para que FCM inicialice
4. `AndroidManifest.xml`: permiso `POST_NOTIFICATIONS` (obligatorio en Android 13+)

### OneSignal — lado servidor (Settings → Push & In-App → Google Android (FCM))
Requiere un **Service Account JSON** de Google (Firebase Cloud Messaging API v1, reemplazó al "Server Key" legacy). Se genera en:

`Google Cloud Console → IAM y administración → Cuentas de servicio → firebase-adminsdk-fbsvc@app-hablavas.iam.gserviceaccount.com → Claves → Crear clave nueva → JSON`

⚠️ **Ojo**: el proyecto puede tener más de una cuenta de servicio (en este caso había 2: `firebase-adminsdk-fbsvc@...` y otra genérica `hablavas@...`). Si subes la clave de la cuenta equivocada, OneSignal rechaza el registro con `Invalid Google Project Number` — hay que usar específicamente la del **Firebase Admin SDK**.

## Incidente resuelto (2026-08-15/16)

**Síntoma**: tras integrar OneSignal, la app dejó de abrir en release — crash nativo antes del Home.

**Causa raíz real**: el trabajo de integración nativa (MainActivity, plugin google-services, `google-services.json`, permiso, appId real) se hizo completo en el servidor de build, pero **nunca se subió a git** — quedó como cambios sin commitear. El commit que llegó a `main` solo traía la parte Dart.

**Fix**: se subieron los cambios pendientes en la rama `fix/ubermoto-app-onesignal-config-nativa` (commit `2a8368e`).

**Segunda vuelta**: con el fix aplicado, la app ya abría y mostraba el diálogo de OneSignal, pero el dispositivo quedaba con estado `Never Subscribed — Invalid Google Project Number` en el dashboard — por el Service Account JSON de la cuenta de servicio equivocada (ver arriba). Se corrigió subiendo la clave correcta. El registro fallido anterior no se auto-corrigió con cerrar/reabrir la app — hubo que **desinstalar y reinstalar** para que el SDK generara una suscripción nueva y limpia.

**Verificación final**: push de prueba enviado desde el dashboard de OneSignal (segmento "Total Subscriptions", 1 destinatario), recibido en el dispositivo con la app cerrada. ✅

Detalle completo de la investigación: [issue #1 del repo front](https://github.com/Jsinnovatech/app_front_ubermotor/issues/1).

## Cómo probar

1. Dashboard OneSignal → Messages → New Push → escribir título/mensaje → Review and Send.
2. O desde el backend: cualquier flujo real (cliente pide viaje, conductor acepta, etc.) dispara el push automáticamente vía `push_service`.
3. Revisar `Audience → Subscriptions` en el dashboard para confirmar que el dispositivo está `Subscribed` (no `Never Subscribed`).
