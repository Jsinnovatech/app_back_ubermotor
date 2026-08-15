---
name: ubermoto-loop
description: "Atencion de INCIDENCIAS del proyecto UBER MOTO / HablaVas (Flutter + FastAPI) en el loop nocturno. Use ONLY when hay una incidencia/bug/reporte/tarea de UberMoto que atender en el tablero (GitHub Issues): leer y reproducir el reporte, identificar flujo → pantalla → secciones, diagnosticar la causa raiz, estructurar la tarea, ponerla en curso, implementar, verificar y reportar. Incluye reglas de producto fijas (precio minimo S/2, motos disponibles, boton azul de ubicacion actual)."
---

# Atención de incidencias — UberMoto / HablaVas (loop nocturno)

El objetivo del skill es **ATENDER INCIDENCIAS**: un reporte de bug o mejora entra
por el tablero (GitHub Issues) y debe salir arreglado, verificado y documentado.
No es "crear tareas por crear": cada incidencia se diagnostica, se arregla y se
reporta.

## Contexto del proyecto

- **Frontend** (Flutter): `/root/2026/app-front-ubermotor` — repo `Jsinnovatech/app_front_ubermotor`
- **Backend** (FastAPI): `/root/2026/app-back-ubermotor` — repo `Jsinnovatech/app_back_ubermotor`
- Token GitHub de jsinnovatech disponible como `GITHUB_JSINNOVATECH_TOKEN` (env) y en los remotes.
- El tablero es **GitHub Issues** del repo correspondiente (front y back por separado).
- Jerarquía: el CEO (Alan) deja la incidencia; el bot (Medium) la atiende de noche
  sola; el Senior revisa el diff al día siguiente y arma el PR.

## Flujo de atención de una incidencia

### Paso 1 — LEER Y REPRODUCIR
- Leer el reporte completo. No inventar el problema: si falta detalle, se marca
  y se pide, no se adivina.
- Identificar **flujo** (cliente / conductor / admin / autoridad / ranking / backend)
  y **pantalla** exacta.
- Reproducir el comportamiento si es posible (código, lógica de estado, API).

### Paso 2 — DIAGNOSTICAR (causa raíz)
- Leer la sección afectada en el código (front y/o back).
- Localizar la causa raíz (no el síntoma). Ej: "no llega push" → verificar si el
  device se registró, si las keys existen, no solo el envío.
- Listar los archivos exactos que se tocarán.

### Paso 3 — ESTRUCTURAR LA TAREA (si no existe issue, crearlo con esta plantilla)
```markdown
## Incidencia
(qué pasa, paso a paso si es bug)

## Flujo
`cliente` | `conductor` | `admin` | `autoridad` | `backend`

## Pantalla
Nombre de la pantalla

## Secciones afectadas
- [ ] Mapa
- [ ] Ubicación actual (botón azul)
- [ ] Ingreso de precios
- [ ] Motos disponibles

## Causa raíz
(lo que encontraste en el diagnóstico)

## Esperado
(cómo debe quedar)

## Criterio de éxito
(qué se verifica para cerrar)

## Repos / ramas
front, back o ambos
```
Sin `Causa raíz`, `Esperado` y `Criterio de éxito` la tarea NO es válida.

### Paso 4 — PONER EN CURSO
- Comentar `En curso` en el issue (mover a in_progress si el tablero lo permite).
- Crear rama propia: `fix/ubermoto-<flujo>-<descripcion-corta>`.
- **NUNCA tocar main ni pushear directo a main.**

### Paso 5 — IMPLEMENTAR Y VERIFICAR
- Tocar SOLO lo necesario (front y/o back).
- Verificar:
  - Front: `flutter analyze` sin errores (infos/warnings pre-existentes OK, no agregar nuevos).
  - Back: `.venv/bin/python -m compileall app` e importar los módulos tocados.
- Commit convencional: `fix(flujo): descripcion` o `feat(flujo): descripcion`.

### Paso 6 — PUSHEAR Y REPORTAR
- Push de la rama.
- Comentar el issue: causa raíz, archivos tocados, verificación corrida, rama.
- No crear el PR (el Senior lo hace tras revisar el diff).

## Mapa de flujos y secciones

| Flujo | Pantallas principales |
|---|---|
| **cliente** | Home (mapa + sheet), Seguimiento del viaje, Historial, Perfil |
| **conductor** | Home (mapa + panel), Registro multipaso (Datos/DNI/Brevete/SOAT/Moto), Validación pendiente, Perfil, Recarga, Historial |
| **admin** | Gestion conductores (lista + carrusel de documentos + aprobar/rechazar), Dashboard |
| **autoridad** (serenazgo/policia) | Central SOS (mapa + sheet) |
| **ranking** | Ranking |
| **backend** | `/app/api/v1/*` + `/app/services/*` |

### Secciones canónicas del flujo cliente (Home)
1. **Mapa** — mapa a pantalla completa con el pin del cliente.
2. **Ubicación actual** — leyenda/indicador; al tocar el **botón azul** se centra en la ubicación actual.
3. **Ingreso de precios** — tarifa con stepper `-/+ 0.50` y campo manual.
4. **Motos disponibles** — lista de conductores cerca con foto (ver reglas de producto).
5. Botón **Solicitar** + toggle pago Efectivo/Yape.

## Reglas de producto FIJAS (aplicar siempre)

1. **Precio mínimo = S/ 2.00** (hoy mal en 3.00). Cambiar TODOS estos:
   - Back: `app/core/config.py` → `TARIFA_MINIMA_CARRERA = 2.0`
   - Back: `app/schemas/viaje.py` → `Field(ge=2.0, ...)`
   - Front: `lib/features/cliente/screens/cliente_home_screen.dart` → `'2.00'`, `_tarifaValor = 2.0`, validación `>= 2.0`, textos "Tarifa mínima S/ 2.00", stepper min 2.00.
2. **Sección "Motos disponibles"** (flujo cliente): cada chofer debe verse **con su foto**. Dos opciones válidas:
   - Opción A: grilla de **2 columnas**, scrollable.
   - Opción B (estilo InDrive, recomendada por defecto): **una fila por chofer**, una debajo de otra, foto visible, sección scrollable.
   Si la tarea no elige layout, usar la **B (InDrive)**.
3. **Mapa — ubicación actual**: existe una leyenda "ubicación actual"; debe haber un **botón azul** que centre el mapa en la ubicación actual del usuario.

## Incidencias típicas ya conocidas (pueden estar pendientes en el tablero)

- Precio mínimo 3.00 en algún texto fijo (debe ser 2.00).
- Sección motos sin foto del conductor o sin scroll.
- Botón de ubicación que no centra el mapa o no pide permiso.
- Push no llega: **diagnosticar la cadena completa** (APP_ID en el APK, keys en
  Railway, device registrado, external id vinculado) antes de tocar código.
- `import 'dart:typed_data'` sin usar en `gestion_conductores_screen.dart`, `perfil_screen.dart`, `registro_documentos_screen.dart`.
- `unnecessary_underscores` (usar `_` en vez de `___`).
