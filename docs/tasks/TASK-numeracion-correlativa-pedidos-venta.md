# TASK-numeracion-correlativa-pedidos-venta: Numeración correlativa de pedidos de venta por período fiscal

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-numeracion-correlativa-pedidos-venta
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/124

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-25 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-25 | INVESTIGATION → DESIGN | NEEDS_ARCHITECTURE, diseño requerido | delivery-start |
| 2026-11-25 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-11-25 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-11-25 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |
| 2026-11-25 | ENGINEERING → REVIEW | Implementación y pruebas escritas; suite backend (2445) y Karma (1664) en verde por verificación propia | delivery-build |
| 2026-11-25 | REVIEW → REVIEW | Quality Gate ciclo 1 (subagente aislado): sin Critical/High; REV-01 y REV-02 (Medium, huecos de prueba) y REV-03/REV-04 (Low) corregidos y marcados Resueltos; se repite el Quality Gate sobre el estado final | delivery-publish |
| 2026-11-25 | REVIEW → PUBLISH | Quality Gate ciclo 2 (subagente aislado): PASS, sin Critical/High; REV-05 (Low) resuelto con una aserción; revisión visual no realizada | delivery-publish |
| 2026-11-25 | PUBLISH → REVIEW | El usuario pidió numerar también los cancelados heredados (cambio de Specification AC-12 aprobado en el chat; PLAN v2, migración `0008`); se repite el Quality Gate | delivery-publish |
| 2026-11-25 | REVIEW → PUBLISH | Quality Gate ciclo 3 (subagente aislado, PLAN v2 / `0008`): PASS, sin Critical/High; REV-06 (Low, documental) resuelto; revisión visual no realizada | delivery-publish |

## Investigación

### Requerimiento
Los pedidos de venta solo tienen UUID; la etiqueta `P-XXXXXXXX` se deriva de él y no se persiste. Se pide un número correlativo de negocio, solo para **ventas** (compras será otra task con serie `NC-xxxxxx`):

- Se asigna al **confirmar** el pedido (`NEW → IN_PREPARATION`), no al crear. Los cancelados conservan su número; nunca se reutiliza.
- El contador se reinicia por **período fiscal de contabilidad** (rango de fechas, no año calendario). El período se determina por `order_date`. Primer pedido confirmado del período = 000001, el siguiente 000002.
- Formato visible de ventas: `NV-000001`.
- **Obligatorio:** prueba de carrera sobre PostgreSQL: dos ventas confirmadas a la vez nunca reciben el mismo número.
- Decisiones del usuario (2026-11-25): sin período fiscal para la fecha del pedido (o Contabilidad deshabilitada) → **bloquear la confirmación**; período **cerrado** → **bloquear**.
- El UUID sigue siendo la clave primaria.

### Hechos encontrados
- `backend/modules/sales/infrastructure/django/models.py:7-45` — `OrderModel` con `id` UUID PK, `company_id`, `order_date`, `status`; sin ningún campo de número.
- `backend/modules/sales/domain/order.py:25-27` — `order_code(order_id)` devuelve `'P-' + 8 hex`; docstring: «no se persiste ni identifica al pedido». `order.py:275-276` — `Order.code` lo usa.
- `backend/modules/sales/domain/order.py:336-341` — `start_preparation()` es la confirmación (`NEW → IN_PREPARATION`, exige ≥1 ítem).
- Hay **dos puntos** de confirmación: `StartOrderPreparation` (`sales/application/commands.py:176-185`) y `PlaceOrder` (`sales/application/placement.py:61`, crea y confirma en un paso; lo usa el formulario único de pedido). La importación de ventas también pasa por `StartOrderPreparation` (`sales/services.py:210`).
- `backend/modules/sales/api/serializers.py:77-78` — `code` = `order_code(obj.id)`; `serializers.py:203` — `order_code` en la vista previa de devolución. `sales/services.py:236` — `ImportedSale.code`. `sales/infrastructure/adapters.py:313` — descripción del asiento: `f'Entrega del pedido {order.code}'`.
- Frontend: todo muestra `code` que llega del API (`order-list.component.html:197,251`, `order-detail.component.html:17`, diálogos de entrega/pago/devolución, `customer-purchase-history.component.html:37`). No calcula la etiqueta. Mapeo en `orders-api.service.ts:144,198` y `customer-orders-api.service.ts:49`.
- No hay búsqueda por texto/código en la lista de pedidos (`sales/api/filters.py`, `sales/infrastructure/django/repositories.py:76-96` solo filtran por estado, canal, cliente, fechas, saldo).
- Patrón de contador existente: `ProformaCounterModel` + `next_number()` con `select_for_update` (`quotations/infrastructure/django/repositories.py:75-81`, `quotations/infrastructure/django/models.py:62-68`) y su gemelo en `receivables` (`receivables/infrastructure/django/models.py:89-95`, `repositories.py:66-68`). Ambos son **por empresa** (clave `company_id`), sin período.
- Períodos fiscales: `FiscalPeriodModel` (`accounting/infrastructure/django/models.py:170-195`: `company_id`, `name`, `start_date`, `end_date`, `status` OPEN/CLOSED; nombre único por empresa sin distinguir mayúsculas). Fachada pública: `accounting.services.period_for(company_id, date)` (`accounting/services.py:328-331`, sin bloquear) y `lock_open_period(company_id, date)` (`services.py:334-351`, bloquea la fila del período con `select_for_update`, exige transacción y lanza `DateOutsideFiscalPeriod` o `FiscalPeriodClosed`).
- `sales` ya depende de la fachada de accounting en infraestructura (`sales/infrastructure/adapters.py:15`).
- `accounting` no es módulo base ni está en `DEFAULT_ENABLED_KEYS` (`modularity/domain/modules.py:57`); una empresa nueva recibe un período fiscal (año en curso) con la configuración por defecto (`accounting/infrastructure/defaults.py:107-109`). `make_company` de tests (`accounts/testing.py:10`) **no** crea período; existe `make_period` en `accounting/tests/journal_support.py:22`.
- Patrón de prueba de concurrencia: `TransactionTestCase` + `_run_together` (`accounting/tests/test_fiscal_period_concurrency.py`, `test_concurrency.py`).
- Pruebas que confirman pedidos sin período (afectadas por el bloqueo): al menos 16 archivos (`sales/tests/*`, `accounting/tests/test_cont13_integration.py`, `test_unified_journey.py`, `reporting/tests/test_api.py`, `modularity/tests/test_enforcement.py`, importación de ventas).
- Último migration de sales: `0005_order_return_and_refund.py`.

### Hipótesis / supuestos no confirmados
- Los pedidos `CANCELLED` anteriores a este cambio no permiten saber si pasaron por la confirmación (no hay historial de transiciones en `OrderModel`). Se asumió no numerarlos; **el usuario lo revirtió** (PLAN v2): se numeran con `0008`.
- Pedidos ya confirmados con `order_date` fuera de cualquier período fiscal: se asume dejarlos sin número (siguen mostrando la etiqueta provisional).
- Que el nombre del período (`FiscalPeriodModel.name`) puede cambiar con `RenamePeriod`; por eso se copia al pedido como instantánea al numerar.

### Módulos y dependencias relacionadas
`sales` (dominio, aplicación, infraestructura, API, migraciones, tests), `accounting` (solo su fachada pública `period_for`/`lock_open_period`), `data_import` (importación de ventas llama a `sales.services`), `customers` (historial de compras muestra `code`), frontend `features/sales` y `features/customers`.

### Implementaciones similares existentes
Contadores por empresa de `quotations` y `receivables` (arriba). `lock_open_period` ya serializa contabilizar vs. cerrar período.

### Comportamiento actual
Confirmar no toca Contabilidad ni exige período; un pedido NEW, IN_PREPARATION, READY, DELIVERED, CANCELLED o RETURNED se muestra con `P-` + 8 hex del UUID.

### Restricciones
Dominio sin Django; módulos sin importarse infraestructura (solo fachada de accounting); nunca editar migraciones aplicadas; aislamiento por `company_id`; textos con i18n es/en/pt; PostgreSQL; avisar antes de instalar dependencias (no se requiere ninguna).

### Riesgos identificados
- Bloquear la confirmación sin período afecta a empresas con Contabilidad deshabilitada y sin período, y a importaciones de ventas con fechas fuera de período (decisión del usuario; se mitiga con mensajes claros).
- La migración de datos lee períodos de `accounting`: dependencia entre apps de migraciones.
- Numerar dentro de la transacción de confirmación: un fallo posterior debe revertir también el número (sin huecos).
- Mucho volumen de pruebas existentes a ajustar.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambio de base de datos con migración de datos sobre pedidos existentes, nueva dependencia de `sales` con la fachada de `accounting`, concurrencia y cambio de contrato API.

### Diseño requerido
**SI** — cambia la identificación visible de los pedidos en lista, detalle y diálogos, y aparece un estado de bloqueo nuevo al confirmar.

## Diseño
Ver `docs/design/DDR-numeracion-correlativa-pedidos-venta-codigo-y-bloqueo.md`.

## Arquitectura
Ver `docs/adr/ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo.md`.

## Plan
`docs/plans/PLAN-2026-11-25-numeracion-correlativa-pedidos-venta.md` (v1, COMPLETO, Specification READY).

## Implementación

**Resumen.** El pedido recibe `(período fiscal, número)` al confirmarse (`NEW → IN_PREPARATION`), dentro de la transacción de la confirmación. `code` pasa a `NV-000001`; los pedidos sin número conservan la etiqueta provisional `P-XXXXXXXX`. El API añade `number` y `fiscal_period {id, name}`.

**Backend (qué cubre cada parte)**
- Dominio `sales/domain/order.py`: `OrderNumber`, `Order.number`, `ensure_confirmable()` y `start_preparation(number)` (INV-01..04, AC-03). `OrderSummary` lleva `number` y `code`.
- Puerto `OrderNumbering` (`application/ports.py`) usado por `StartOrderPreparation` y `PlaceOrder` (AC-02, AC-05, AC-06, AC-10); `ensure_confirmable()` corre antes de numerar para no consumir número en confirmaciones inválidas (EDGE-01).
- Adaptador `OrderNumberingAdapter` (`infrastructure/adapters.py`): `accounting.services.lock_open_period` + contador con `select_for_update`; traduce a `fiscal_period_missing` / `fiscal_period_closed` (409 por el `RuleConflict` existente). Descripción del asiento de entrega con el período (AC-11).
- Modelos y migraciones: `0006` (columnas nulas, `OrderNumberCounterModel`, restricción única parcial y dos CHECK) `0007` (numeración del histórico confirmado) y `0008` (numera los CANCELLED heredados a continuación; PLAN v2; ambas repetibles; AC-12).
- API: `code`, `number`, `fiscal_period` en lista y detalle (API-01..03).

**Frontend.** `fiscalPeriod` en modelo y mapeo; lista (tabla y tarjetas) y detalle muestran el período solo si hay número (UI-01, UI-02); componente `app-fiscal-period-alert` (enlace a Contabilidad solo si el módulo está habilitado) en detalle y en `order-create` (UI-03); claves es/en/pt `SALES.FISCAL_PERIOD.*`, `SALES.ORDER_LIST.PERIODO`, `SALES.ORDER_DETAIL.PERIODO_FISCAL`. Diálogos e historial de clientes consumen `code` sin cambios (UI-04). Pantallas de referencia: Lista y «Detalle de documento en curso» del sistema de diseño; sin componentes nuevos de `shared/`.

**Pruebas añadidas.** `test_order_number_domain` (dominio y casos de uso con fakes), `test_order_numbering` (serie por período/empresa, `order_date`, cancelados, snapshot, bloqueos, rollback, restricciones de BD, API), `test_order_numbering_concurrency` (8 confirmaciones simultáneas → `{1..8}`; dos períodos y dos empresas; mismo pedido dos veces; confirmar vs. cerrar), `test_order_number_migration` (0007 e idempotencia). Karma: `fiscal-period-alert`, detalle, `order-create`, lista y servicio. **Mutación comprobada:** quitando `lock_open_period` y `select_for_update`, las tres pruebas de carrera de numeración fallan; con ellos pasan.

**Pruebas heredadas ajustadas.** Fixture `sales/tests/periods.py` (período abierto amplio) en `SalesApiTestCase`, `DeliveryTestCase` y en los tests de importación que confirman pedidos; `FakeOrderNumbering`/`fake_number` en `sales/tests/fakes.py`; claves nuevas en `DETAIL_KEYS`/`SUMMARY_KEYS`; `Books` reemplaza el período amplio por el suyo.

**Desviaciones respecto al plan.**
- `ensure_confirmable()` es un método nuevo del agregado (no estaba en el plan): permite validar antes de numerar. Detalle de implementación.
- La migración `0007` depende de `('accounting', '0009_fiscal_period')`, como anticipó el ADR.
- Enlace de la alerta: `/pocketbiz/accounting/settings?tab=periods` (la pestaña `periods` ya existe).
- Para ejecutar pruebas se copió `backend/.env` del repositorio principal (con autorización del usuario) y se enlazó `node_modules`; ambos están en `.gitignore`.

**Deuda técnica / notas.** Contador no extraído a `shared/` (ADR decisión 7). Pedidos heredados con fecha fuera de todo período siguen con etiqueta provisional (limitación conocida); los cancelados heredados se numeran con `0008` (PLAN v2). Sin Contabilidad/sin período no se puede confirmar (decisión del usuario). Avisos de lint previos sin tocar (E501/E301 en archivos de `sales`); cero avisos nuevos en líneas cambiadas (`flake8`/`ruff`).

**Verificación propia (no es el Quality Gate).** `ng lint` y `i18n:check` sin hallazgos; `ng build` compila; Karma de `features` y `core`: 1664 pruebas OK; backend: pruebas de `sales`, `reporting`, `customers`, `data_import`, `modularity`, `accounting` y las nuevas en verde en la corrida por módulos; suite completa del backend (`python manage.py test`, PostgreSQL): 2445 pruebas OK. Una primera corrida de la suite completa dio cientos de errores por ejecutarse a la vez que otra sobre la misma base de pruebas; repetida sola y con base propia, quedaron 3 fallos reales (dos pruebas de `sales` que esperaban la etiqueta antigua en la referencia del movimiento de inventario y la guarda `company_id` indexado del contador), corregidos y re-ejecutada la suite completa en verde. `0006` se regeneró antes de cualquier merge para indexar `company_id` del contador.

## Review

**Ciclo 1 (subagente aislado, contexto limpio).** Ejecutó: suite completa del backend (2445 OK), Karma completo (1844 OK), `ng lint`, `i18n:check`, `ng build`, `ruff`/`flake8` (0 avisos en líneas cambiadas) y `bandit` (sin hallazgos); `npm audit` y revisión visual en navegador no se realizaron. Veredicto: sin Critical/High, con 4 hallazgos:
- [REV-01](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-01.md) (Medium) prueba AC-08 débil → Resuelto (verificado por mutación).
- [REV-02](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-02.md) (Medium) sin prueba de importación con período faltante/cerrado → Resuelto.
- [REV-03](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-03.md) (Low) vista previa de devolución sin aserción → Resuelto.
- [REV-04](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-04.md) (Low) aviso de período cerrado sin nombre → Resuelto.

**Ciclo 2 (subagente aislado, estado final).** Ejecutó: backend completo `Ran 2449 tests ... OK` (PostgreSQL), Karma `TOTAL: 1847 SUCCESS`, `ng lint` sin hallazgos, `i18n:check` 2510 claves / 0 faltantes, `ng build` compila, `ruff`/`flake8` sin avisos en líneas cambiadas, `bandit` sin hallazgos. Verificó REV-01..04 (REV-01 con mutación propia: sin `lock_open_period` fallan 2 de 5 pruebas de carrera). **Veredicto: PASS**, sin Critical/High. Hallazgo nuevo:
- [REV-05](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-05.md) (Low) sin aserción de `period` en el 409 → Resuelto con una aserción añadida después del gate y una ejecución dirigida (`test_order_numbering`: 19 OK); el resto del estado quedó cubierto por el ciclo 2.

**Ciclo 3 (subagente aislado, tras el PLAN v2 y la migración `0008`).** Ejecutó: backend completo `Ran 2451 tests ... OK` (base creada de cero con las 8 migraciones de `sales`), `makemigrations --check`: sin cambios, Karma `TOTAL: 1847 SUCCESS`, `ng lint` sin hallazgos, `i18n:check` 2510 / 0 faltantes, `ng build` compila, `ruff`/`flake8` sin avisos en líneas cambiadas, bandit sin hallazgos en el diff. Revisó `0008` (idempotencia, orden, continuidad del contador, NEW y fuera de período sin número, empresas independientes) y la coherencia documental. **Veredicto: PASS.** Hallazgo nuevo: [REV-06](../reviews/REV-2026-11-25-numeracion-correlativa-pedidos-venta-06.md) (Low, documental: descripción del PR y TASK no mencionaban `0008`) → Resuelto. Brecha menor anotada: ninguna prueba de `0008` cubre un cancelado con fecha en período cerrado (se numera igual que en `0007`, que sí lo prueba).

**No verificado:** revisión visual en navegador (móvil/escritorio, claro/oscuro), `npm audit`, estabilidad de las pruebas con hilos en repeticiones, y las migraciones `0007`/`0008` contra datos reales.

## Publicación

PR https://github.com/rolion/dore-mini-erp/pull/124 listo para aprobación humana (no se mergea). Cambio sensible: **base de datos** (migraciones `0006`, `0007` y `0008` sobre `sales_order`, con numeración del histórico) y **arquitectura** (ADR `ADR-numeracion-correlativa-pedidos-venta-contador-por-periodo`); lo aprueba un humano. Antes del merge conviene probar `0007` y `0008` contra una copia de producción; el despliegue ya hace backup antes de `migrate`.
