# TASK-administrar-cuentas-codigo-clasificacion-estado: Administrar cuentas con código, nombre, clasificación y estado (CONT-09)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-administrar-cuentas-codigo-clasificacion-estado (base: `task/TASK-configurar-seis-clasificaciones-contables`, PR #79 de CONT-08 aún sin mergear)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/80
**Fuente:** https://trello.com/c/6XUugVjJ

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-09 | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN | Cambia la pantalla de cuentas | delivery-start |
| 2026-11-16 | DESIGN → ARCHITECTURE | Cambia el contrato de la cuenta (código, clasificación obligatoria, tipo de dinero opcional) | delivery-start |
| 2026-11-16 | ARCHITECTURE → PLANNING | DDR y ADR escritos | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY | delivery-start |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-09 (insumo, no Specification aprobada). Depende de CONT-08. Base de trabajo: rama `accounting`; no se mergea a `main`.
- Unificar el plan de cuentas en el submenú Cuentas: listar, agregar, editar y habilitar/deshabilitar; código y nombre obligatorios, clasificación obligatoria; código único por empresa.
- Al crear una cuenta, ofrecer solo clasificaciones habilitadas.
- Impedir cambiar la clasificación de una cuenta con asientos confirmados; permitir renombrar sin alterar históricos; no ofrecer borrado.
- Las cuentas deshabilitadas siguen en consultas y saldos, pero no en nuevos asientos ni configuraciones.
- Si se deshabilita una cuenta usada por una configuración automática, mostrar su impacto; la operación posterior debe pedir corregir la configuración, sin sustituciones silenciosas.
- Aceptación: (1) crear Caja/101/Activo; rechazar código repetido en la misma empresa y permitirlo en otra; (2) deshabilitar Caja la oculta en formularios nuevos y mantiene historial y saldos; (3) rechazar cambio de clasificación de una cuenta utilizada y aceptar el cambio de nombre.

Aclaraciones del dueño (2026-11-16):
- El plan de cuentas que se cargará después (**no se carga en esta tarea**) tiene 40 cuentas con código jerárquico `1.1.01 … 6.2.02`, nombre y una de las seis clasificaciones.
- «Depreciación acumulada» (1.2.05) es de Activo pero **cuenta correctora** (saldo acreedor); el diseño decide cómo marcarla.
- Solo algunas cuentas de Activo son de dinero (Caja 1.1.01, Bancos 1.1.02); hoy el tipo Caja/Banco/Billetera es obligatorio y no aplica al resto.
- Decisión sobre deshabilitar una cuenta usada por métodos de pago: **seguir bloqueando** con el 409 actual que lista los métodos afectados (respuesta del dueño a la pregunta de la tarjeta).

### Hechos encontrados
- `backend/modules/accounting/domain/account.py:78-105` — `Account` tiene `name`, `currency`, `kind` (nulable), `account_class` (nulable, CONT-08) y `opening_balance`; **no tiene código**. `Account.create` valida el nombre y la moneda; `kind` no es obligatorio en el dominio.
- `backend/modules/accounting/api/serializers.py:16-28` — el serializer de alta exige `kind`; es el único lugar donde es obligatorio hoy (`AccountInputSerializer`).
- `backend/modules/accounting/application/use_cases.py:62-123` — `UpdateAccount` ya bloquea cambiar moneda y apertura si hay entradas (`account_has_entries`, `use_cases.py:90,102`) usando `has_entries_for_account` (`infrastructure/django/repositories.py:317`); es el patrón para bloquear la clasificación. `DeactivateAccount` (`use_cases.py:125-140`) responde 409 `account_in_use` con los métodos afectados.
- `backend/modules/accounting/infrastructure/django/models.py:8-30` — único `(lower(name), company_id)`; `account_class` y la tabla `accounting_account_class_setting` llegan en `0007` (CONT-08).
- `backend/modules/accounting/services.py:63-75` — `validate_money_account` rechaza cuentas inexistentes o inactivas para usos nuevos; `resolve_account` (`services.py:42`) usa `can_receive` (activa y en BOB).
- `frontend/panel_admin/src/app/features/accounting/components/accounts-tab/accounts-tab.component.html:37-44` — la tabla muestra Nombre, Tipo, Moneda, Apertura, Estado y Acciones; el diálogo (`account-dialog`) exige tipo y ofrece clasificación opcional (CONT-08).
- La base local quedó vacía de cuentas (limpieza del 2026-11-16): no hay datos que migrar localmente. Producción puede tener cuentas anteriores (sin tipo, sin clasificación, sin código).
- `docs/adr/ADR-configurar-seis-clasificaciones-contables-catalogo-fijo-y-validacion.md` — decisión 4: código y obligatoriedad quedan para CONT-09, sin reabrir el contrato.

### Hipótesis / supuestos no confirmados
- «Asientos confirmados» equivale hoy a las entradas del libro de una sola cuenta (`accounting_entry`); cuando CONT-02 introduzca asientos con líneas, la comprobación se apoyará en las líneas de la cuenta.
- El código admite letras, dígitos, punto, guion y guion bajo, hasta 20 caracteres, sin espacios, y es único sin distinguir mayúsculas. Es decisión de este TASK, no del dueño.

### Módulos y dependencias relacionadas
`accounting` (dueño). Los módulos que crean cobros/pagos consumen la fachada (`resolve_account`, `validate_money_account`), que no cambia.

### Implementaciones similares existentes
`UpdateAccount` (bloqueos por entradas), `AccountConflict`, el diálogo `account-dialog` y la pestaña `accounts-tab` (plantilla de configuración con listados).

### Comportamiento actual
Las cuentas son destinos de cobros y pagos: nombre, moneda, tipo Caja/Banco/Billetera obligatorio, sin código; la clasificación contable es opcional (CONT-08).

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, no editar migraciones aplicadas, dominio sin Django, sin texto hardcodeado en el frontend (es/en/pt), sin `float`. Tarjeta: sin borrado de cuentas; sin sustituciones silenciosas. Decisión del dueño: sin cargar el plan de cuentas aquí.

### Riesgos identificados
- Alta de cuenta: pasa a exigir código y clasificación (cambio de contrato; el único cliente es el panel, que se actualiza en el mismo PR).
- Cuentas anteriores sin código ni clasificación: siguen operando; se completan al editarlas.
- Con un plan completo, el selector de destino de los métodos de pago listará también cuentas que no son de dinero: lo resuelve CONT-12 (mapeo a Caja/Banco), fuera de esta tarea.
- El bloqueo por «asientos confirmados» usa entradas de una sola cuenta hasta CONT-02.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el modelo de la cuenta (migración), el contrato del API y las reglas de dominio, y lo consumen CONT-02, CONT-04, CONT-11 y CONT-12.

### Diseño requerido
**SI** — cambian la lista y el diálogo de cuentas.

## Diseño
`docs/design/DDR-administrar-cuentas-codigo-clasificacion-estado-lista-y-formulario-de-cuentas.md`.

## Arquitectura
`docs/adr/ADR-administrar-cuentas-codigo-clasificacion-estado-modelo-de-cuenta.md`.

## Plan
`docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md` (v1) · Modo: COMPLETO · Specification readiness: READY.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
