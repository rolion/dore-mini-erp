# TASK-configurar-seis-clasificaciones-contables: Configurar las seis clasificaciones contables (CONT-08)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configurar-seis-clasificaciones-contables (base: `accounting`)
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/F7HOgd65

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-08 | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN | Pantalla nueva en Configuración | delivery-start |
| 2026-11-16 | DESIGN → ARCHITECTURE | Contrato nuevo de datos y fachada que consumirá CONT-09 | delivery-start |
| 2026-11-16 | ARCHITECTURE → PLANNING | DDR y ADR escritos | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY | delivery-start |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-08 (insumo, no Specification aprobada). Base de trabajo: rama `accounting` (lo hecho allí no está en `main`); no se mergea a `main`.
- Objetivo: simplificar Configuración con clasificaciones predefinidas.
- Activo, Pasivo, Patrimonio, Ingresos, Gastos y Costos; solo habilitar/deshabilitar por empresa, sin crear, renombrar ni borrar.
- Una clasificación deshabilitada no aparece al crear cuentas y la API también rechaza su selección.
- No deshabilitar automáticamente cuentas existentes ni alterar históricos o saldos; las cuentas existentes conservan su clasificación y siguen operando según su propio estado.
- Aceptación: (1) aparecen exactamente seis, incluida Ingresos; (2) deshabilitar Costos en A impide nuevas cuentas de esa clasificación en A sin afectar B; (3) una cuenta existente de Costos mantiene clasificación, movimientos y disponibilidad según su propio estado.
- Dependencia: CONT-07 (entregada en el PR #78). Reglas transversales: API y UI con aislamiento por empresa y permisos existentes; decimales y moneda existentes.
- Contexto del tablero: CONT-09 (cuentas con código, nombre, clasificación obligatoria y estado) depende de esta tarjeta; CONT-11 pone Clasificaciones dentro de Configuración.

### Hechos encontrados
- `backend/modules/accounting/infrastructure/django/models.py:60-77` — `ClassificationModel` (`accounting_classification`) es el catálogo CONT-01: nombre libre, `direction` INCOME/EXPENSE, crear/renombrar/activar. Es «por qué se mueve el dinero» y **no** equivale a las seis nuevas (ADR de CONT-07, decisión 4).
- `backend/modules/accounting/domain/account.py:78-89` — `Account` solo tiene `kind` (CASH/BANK/WALLET, nulable) y `opening_balance`; **no tiene clasificación contable ni código**.
- `backend/modules/accounting/services.py:63-92` — fachada con `validate_money_account` y `validate_classification` (la de CONT-01); patrón a seguir para la validación nueva.
- `backend/modules/accounting/api/urls.py:28-34` y `api/views.py:118-223` — vistas de configuración con `_ConfigView` (`required_modules = ()`, permiso de administrador de empresa).
- `frontend/panel_admin/src/app/features/accounting/pages/accounting-settings/accounting-settings.component.html:32-57` — pestañas de Configuración; la pestaña «Clasificaciones» gestiona el catálogo CONT-01 (`components/classifications-tab/`).
- No existen seeds ni fixtures de `accounting` (CONT-07): los catálogos los crea cada empresa; hoy hay 21 empresas locales, todas de prueba según el dueño.
- Migraciones `accounting` 0001–0006 aplicadas en la base local; la siguiente es `0007`.

### Hipótesis / supuestos no confirmados
- El ensayo de CONT-07 sobre una copia confirmó que `migrate` aditivo no altera datos; una migración nueva con una tabla vacía mantiene esa propiedad.
- Que la UI llame «Clasificaciones contables» a las seis y deje la pestaña CONT-01 intacta hasta que una tarea posterior la retire es una decisión de este TASK (ver DDR), no del dueño.

### Módulos y dependencias relacionadas
`accounting` (dueño). Ningún otro módulo cambia. CONT-09 consumirá la fachada nueva; Gastos/Compras no se tocan.

### Implementaciones similares existentes
`SettingsModel`/`CoveragePeriodModel` (`models.py:31-58`) para configuración por empresa; `SetClassificationActive` y las vistas `activate/deactivate` (`views.py:212-223`) para el patrón de habilitar/deshabilitar con permisos; pestañas de `features/accounting/components/` para la UI.

### Comportamiento actual
No hay seis clasificaciones. La cuenta no se clasifica contablemente; las clasificaciones CONT-01 son otra cosa.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, no editar migraciones aplicadas, dominio sin Django, sin texto hardcodeado en el frontend (es/en/pt). Tarjeta: sin crear/renombrar/borrar; sin efectos sobre cuentas existentes; no mergear a `main`.

### Riesgos identificados
- **Colisión de nombres** con el catálogo CONT-01 («clasificación»): mitigada con nombre propio de código y de API (`account-classes`).
- La tarjeta pide rechazar clasificaciones deshabilitadas «al crear cuentas», pero hoy la cuenta no tiene clasificación: se añade un campo nulable mínimo (ver ADR); la obligatoriedad y el código son de CONT-09.
- Existencia de las seis por empresa sin sembrar datos: se resuelve guardando solo el estado deshabilitado (ver ADR).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — modelo y contrato nuevos (tabla, columna, fachada, API) que consumen CONT-09 y siguientes.

### Diseño requerido
**SI** — pantalla nueva dentro de Configuración.

## Diseño
`docs/design/DDR-configurar-seis-clasificaciones-contables-pestana-de-configuracion.md`.

## Arquitectura
`docs/adr/ADR-configurar-seis-clasificaciones-contables-catalogo-fijo-y-validacion.md`.

## Plan
`docs/plans/PLAN-2026-11-16-configurar-seis-clasificaciones-contables.md` (v1) · Modo: COMPLETO · Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
