# TASK-politica-stock-negativo: Aplicar la política de stock negativo (PB-INV-007)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-politica-stock-negativo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/26

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-29 | (nuevo) → INVESTIGATION | Task creado; rama desde `main` al día | delivery-start |
| 2026-10-29 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | Nuevo ajuste por empresa, nueva dependencia inventory → modularity y contrato 409 | delivery-start |
| 2026-10-29 | PLANNING → ENGINEERING | Specification READY tras respuestas del usuario (ver Plan) | delivery-start |

## Investigación

### Requerimiento
**PB-INV-007 · Aplicar la política de stock negativo** (Inventario, P1, dep. PB-INV-004 y PB-CFG-001). Como administrador, quiero definir si se permite stock negativo para controlar salidas según mi operación.

- Menú y vista: Inventario → Configuración → General. Campo «Permitir stock negativo», desactivado por defecto, con descripción de su efecto en entregas, ajustes y reversión de recepciones.
- Pantallas afectadas: confirmación de entrega, ajuste y reversión. Ante saldo insuficiente se muestran producto, almacén, cantidad solicitada y existencia actual.
- Acciones: guardar la política; al habilitarla, confirmar una explicación breve de que podrán existir saldos negativos. El formulario fallido de una operación conserva sus datos.
- Aceptación de interfaz y concurrencia: con bloqueo activo, dos entregas simultáneas que exceden las existencias no se confirman ambas; la rechazada explica la insuficiencia y no deja salida ni entrega parcial.
- AC: (1) la configuración por empresa bloquea el stock negativo por defecto; permitirlo exige elección explícita; (2) con bloqueo activo una salida insuficiente no crea movimiento ni confirma la entrega asociada; (3) dos salidas simultáneas no consumen las mismas unidades: validación y cambio de saldo son atómicos.

**Aclaraciones del usuario (2026-10-29):**
1. Alcance de entregas: **solo política + Inventario**. Ventas NO se conecta todavía (confirmar una entrega no descuenta stock); la historia que descuente stock al entregar consumirá la política ya lista.
2. El 409 por saldo insuficiente lleva datos estructurados: producto, almacén, cantidad solicitada y existencia actual.

### Hechos encontrados
- `backend/modules/inventory/application/movement_use_cases.py:28-65` — `RecordMovement.execute(..., allow_negative=False)`: valida bajo `repository.locked(warehouse_id)`; `_check_balance` (`:61-65`) lanza `MovementConflict('insufficient_stock', 'No hay saldo suficiente para registrar la salida.')` sin datos del producto/almacén/saldo.
- `movement_use_cases.py:68-87` — `ReverseMovement.execute(..., allow_negative=False)`: bloquea, calcula el contramovimiento y, si es salida, compara con el saldo (`:81-84`); sin endpoint HTTP aún (lo trae PB-INV-008).
- `backend/modules/inventory/infrastructure/django/movement_repository.py:97-101,118-121` — `locked()` = `transaction.atomic()` + `select_for_update` del almacén (serializa salidas simultáneas); `balance()` suma el libro. Es el mecanismo de atomicidad (AC-3) ya existente.
- `backend/modules/inventory/services.py:40-65` — fachada `record_movement`/`reverse_movement` con `allow_negative` como parámetro **que decide quien llama**: nada hoy lee una política por empresa.
- `backend/modules/inventory/application/adjustment_use_cases.py:73-81` — `ConfirmAdjustment` llama a `RecordMovement` con el valor por defecto (bloqueado) dentro del bloqueo del almacén; la cantidad contada es ≥ 0 y la diferencia se calcula contra el saldo vigente, por lo que un ajuste nunca deja saldo negativo (la política no cambia su resultado, pero debe ser la misma ruta).
- `backend/modules/inventory/api/stock_views.py:116` — único lugar que traduce `MovementConflict` a HTTP (apertura de existencias); `backend/modules/inventory/api/views.py:27-29` — excepción `Conflict` 409 `{detail, code}`.
- `backend/modules/sales/application/commands.py:163-171` — `DeliverOrder` solo cambia el estado del pedido; el pedido no tiene almacén ni líneas con control de stock en la entrega (grep de `warehouse|inventory|stock` en `modules/sales` sin coincidencias fuera de tests). No existe módulo de compras ni recepciones. Por eso la aplicación a entregas y recepciones se limita a dejar la política lista.
- `backend/modules/modularity/domain/settings.py:39-54` — catálogo de ajustes en código; `CHOICE`/`PERCENT` únicos tipos (`:9-10`, `:73-77`); `settings_for('inventory')` está vacío; `display()` (`:123-127`) escribe el historial.
- `backend/modules/modularity/application/settings_use_cases.py:44-73` — `UpdateModuleSettings` guarda en bloque, valida habilitación y registra historial con actor.
- `backend/modules/modularity/services.py:13-30` — fachada de solo lectura `get_sales_settings` (DTO inmutable, `company_id` primero).
- `backend/modules/sales/tests/test_boundaries.py:9-23` — mapa de dependencias permitidas: `'inventory': {'catalog'}`; `modularity` solo permitido a `sales` (`:17`, `:21`).
- `frontend/panel_admin/src/app/app.routes.ts:181-187` — `inventory/settings` ya monta `ModuleSettingsComponent` (pestañas General e Historial); `features/settings/models/setting.ts:1` y `settings-api.service.ts:17` limitan `kind` a `'choice' | 'percent'`; `module-settings.component.html:47-63` solo pinta select o porcentaje.
- `frontend/panel_admin/src/app/features/inventory/pages/adjustment-form/adjustment-form.component.ts:222-293` — manejo de 409/400 que conserva el formulario (`balance_changed`, `conflictMessage`).
- `frontend/panel_admin/src/app/features/settings/components/module-confirm-dialog/` — diálogo de confirmación reutilizable para el patrón «confirmar al habilitar».

### Hipótesis / supuestos no confirmados
- La política aplica por igual a todas las salidas del libro (entrega, ajuste, reversión de recepción): una sola regla en `RecordMovement`/`ReverseMovement`, sin excepciones por origen.
- Habilitar la política no modifica saldos existentes; deshabilitarla con saldos negativos ya existentes no los corrige ni bloquea entradas (solo bloquea nuevas salidas insuficientes).
- «Cantidad solicitada» en la reversión = cantidad del contramovimiento.

### Módulos y dependencias relacionadas
`inventory` (aplica la política), `modularity` (dueño del ajuste, historial y API de configuración), frontend `features/settings` (campo booleano + confirmación) y `features/inventory` (mensaje de saldo insuficiente). `sales` no cambia.

### Implementaciones similares existentes
Ajustes de Ventas (`get_sales_settings` + `SalesSettingsReader` en `sales/application/ports.py`, adaptador en `sales/infrastructure/adapters.py`) como patrón de lectura de configuración entre módulos.

### Comportamiento actual
Las salidas ya se bloquean por defecto (`allow_negative=False`), pero la empresa no puede cambiarlo, el 409 no informa producto/almacén/solicitado/existente y no hay forma de permitir saldos negativos desde la UI.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dominio sin Django, módulos de negocio sin importar `accounts`, `Decimal`, no editar migraciones aplicadas (este cambio no necesita migración: el ajuste se guarda en la tabla genérica de configuración), español.

### Riesgos identificados
- Nueva dependencia `inventory → modularity` (acotada a una fachada; test de frontera).
- La política debe leerse **dentro** del bloqueo del almacén para que dos solicitudes no vean valores distintos a mitad de la operación.
- `allow_negative` como parámetro público de la fachada permite saltarse la política: debe quedar derivado de la política de la empresa.
- Suite frontend con fallos preexistentes (comparar contra la línea base).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — decisión de dónde vive y quién lee la política, nueva dependencia entre módulos, nuevo tipo de ajuste (booleano) en el contrato de configuración y contrato 409 con datos estructurados.

### Diseño requerido
**SI** — campo con confirmación al habilitar y estados de error con datos en formularios.

## Diseño
Ver `docs/design/DDR-politica-stock-negativo-campo-y-mensaje-saldo-insuficiente.md`.

## Arquitectura
Ver `docs/adr/ADR-politica-stock-negativo-lectura-y-aplicacion-de-la-politica.md`.

## Plan
`docs/plans/PLAN-2026-10-29-politica-stock-negativo.md` (v1, COMPLETO, READY).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
