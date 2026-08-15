# Skill: ubermoto-loop (Loop nocturno — UberMoto / HablaVas)

> Este es el contenido del skill de opencode `ubermoto-loop`, copiado en los docs
> del proyecto para que quede versionado. La versión activa vive en
> `~/.config/opencode/skills/ubermoto-loop/SKILL.md` del servidor.

## Contexto del proyecto

- **Frontend** (Flutter): `/root/2026/app-front-ubermotor` — repo `Jsinnovatech/app_front_ubermotor`
- **Backend** (FastAPI): `/root/2026/app-back-ubermotor` — repo `Jsinnovatech/app_back_ubermotor`
- Token GitHub de jsinnovatech disponible como `GITHUB_JSINNOVATECH_TOKEN` (env) y en los remotes.
- El tablero es **GitHub Issues** del repo correspondiente (front y back por separado).
- El CEO (Alan) deja la tarea; el bot la ejecuta sola de noche; el Senior revisa el diff al día siguiente.

## Paso 0 — Identificar el flujo

Siempre clasificar la tarea por flujo antes de tocarla:

| Flujo | App | Pantallas principales |
|---|---|---|
| **cliente** | front | Home (mapa + sheet), Seguimiento del viaje, Historial, Perfil |
| **conductor** | front | Home (mapa + panel), Registro multipaso (Datos/DNI/Brevete/SOAT/Moto), Validación pendiente, Perfil, Recarga, Historial |
| **admin** | front | Gestion conductores (lista + carrusel de documentos + aprobar/rechazar), Dashboard |
| **autoridad** (serenazgo/policia) | front | Central SOS (mapa + sheet) |
| **ranking** | front | Ranking |
| **backend** | back | `/app/api/v1/*` + `/app/services/*` |

### Secciones canónicas del flujo cliente (Home)
1. **Mapa** — mapa a pantalla completa con el pin del cliente.
2. **Ubicación actual** — leyenda/indicador; al tocar el **botón azul** se centra en la ubicación actual.
3. **Ingreso de precios** — tarifa con stepper `-/+ 0.50` y campo manual.
4. **Motos disponibles** — lista de conductores cerca con foto (ver reglas de producto).
5. Botón **Solicitar** + toggle pago Efectivo/Yape.

## Paso 1 — Crear/estructurar la tarea

Si no existe el issue, crearlo SIEMPRE con esta plantilla (si ya existe, validar que la tenga):

```markdown
## Flujo
`cliente` | `conductor` | `admin` | `autoridad` | `backend`

## Pantalla
Nombre de la pantalla (ej. Home del cliente)

## Secciones afectadas
- [ ] Mapa
- [ ] Ubicación actual (botón azul)
- [ ] Ingreso de precios
- [ ] Motos disponibles

## Problema
(qué está mal / qué se quiere)

## Esperado
(cómo debe quedar, conciso)

## Criterio de éxito
(qué se verifica para dar por cerrada la tarea)

## Repos / ramas
front o back (o ambos)
```

Una tarea sin `Problema`, `Esperado` y `Criterio de éxito` NO es válida: completarla antes de empezar.

## Paso 2 — Poner en curso

- Marcar el issue como en curso (comentar `En curso` y mover a in_progress si el tablero lo permite).
- Crear rama propia: `fix/ubermoto-<flujo>-<descripcion-corta>` (ej. `fix/ubermoto-cliente-precio-minimo`).
- **NUNCA tocar main ni pushear directo a main.**

## Paso 3 — Implementar y verificar

- Trabajar en el repo local correspondiente (front `/root/2026/app-front-ubermotor`, back `/root/2026/app-back-ubermotor`).
- Verificar antes de commitear:
  - Front: `flutter analyze` sin errores (infos/warnings pre-existentes OK, no agregar nuevos).
  - Back: `.venv/bin/python -m compileall app` e importar los módulos tocados.
- Commit con mensaje convencional: `fix(flujo): descripcion` o `feat(flujo): descripcion`.

## Paso 4 — Push + reportar

- Push de la rama.
- Comentar el issue: qué se cambió, archivos, verificación corrida, y la rama.
- No crear el PR (eso lo hace el Senior tras revisar el diff).

## Reglas de producto FIJAS (aplicar siempre)

1. **Precio mínimo = S/ 2.00** (hoy mal en 3.00). Cambiar TODOS estos:
   - Back: `app/core/config.py` → `TARIFA_MINIMA_CARRERA = 2.0`
   - Back: `app/schemas/viaje.py` → `Field(ge=2.0, ...)`
   - Front: `lib/features/cliente/screens/cliente_home_screen.dart` → `'2.00'`, `_tarifaValor = 2.0`, validación `>= 2.0`, textos "Tarifa mínima S/ 2.00", stepper min 2.00.
2. **Sección "Motos disponibles"** (flujo cliente): cada chofer debe verse **con su foto**. Dos opciones válidas:
   - Opción A: grilla de **2 columnas**, scrollable.
   - Opción B (estilo InDrive, la recomendada por defecto): **una fila por chofer**, una debajo de otra, foto visible, sección scrollable.
   Si la tarea no elige layout, usar la **B (InDrive)**.
3. **Mapa — ubicación actual**: existe una leyenda "ubicación actual"; debe haber un **botón azul** que centre el mapa en la ubicación actual del usuario.

## Errores comunes a revisar en fixes de UberMoto

- Precio mínimo 3.00 en algún texto fijo (debe ser 2.00).
- Sección motos sin foto del conductor o sin scroll.
- Botón de ubicación que no centra el mapa o no pide permiso de ubicación.
- `import 'dart:typed_data'` sin usar en `gestion_conductores_screen.dart`, `perfil_screen.dart`, `registro_documentos_screen.dart`.
- `unnecessary_underscores` (usar `_` en vez de `___`).
