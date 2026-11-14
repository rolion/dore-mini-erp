# TASK-conciliar-regularizar-pagos-historicos: Conciliar y regularizar pagos históricos de productos y servicios (PB-ACC-004)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-conciliar-regularizar-pagos-historicos
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/71
**Fuente:** https://trello.com/c/17DwVe39/21-pb-acc-004-conciliar-y-regularizar-pagos-hist%C3%B3ricos-de-productos-y-servicios

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-14 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (f45b0cd, incluye PB-ACC-003 y PB-COB-002) | delivery-start |
| 2026-11-14 | INVESTIGATION → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (dinero, nueva dependencia accounting → sales/receivables, migración); sin UI | delivery-start |
| 2026-11-14 | PLANNING → ENGINEERING | Specification READY: la tarjeta fija las reglas; las decisiones técnicas están en el ADR | delivery-start |
| 2026-11-14 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-11-14 | REVIEW → PUBLISH | Quality Gate PASS (2 hallazgos Low abiertos); a la espera de aprobación humana | delivery-publish |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-ACC-004 (P1; **no es una Specification aprobada**). Historia: como administrador, completar entradas faltantes de pagos anteriores sin cambiar cobros ni duplicar dinero. Esperado: proceso administrativo/command con previsualización obligatoria antes de aplicar, filtrable por empresa y periodo; comparar pagos de pedidos y de receivables contra el libro por la identidad estable del origen; mostrar cantidades e importes de faltantes, existentes y excluidos/conflictivos, separados por origen, cuenta y moneda. Mapeo explícito para métodos históricos (con correspondencia por periodo si cambió el destino); no inferir cuentas ni atribuir la autoría del cobro a quien regulariza; conservar fecha efectiva, monto, método, referencia y autor original cuando exista; registrar aparte fecha/usuario de regularización; reportar campos ausentes sin inventarlos. Aplicar solo faltantes válidos; excluir pagos realmente anulados si ese estado existe; el pago conservado de un pedido cancelado sigue siendo elegible; casos ambiguos se reportan sin modificar; no alterar pagos, imputaciones ni saldos. Repetible y seguro ante concurrencia con cobros nuevos; resumen de resultados y errores; reportar diferencias de importes o destinos de entradas existentes sin sobrescribirlas. Criterios: dataset con faltante / existente / pedido cancelado con pago conservado (previsualización no escribe, aplicación crea solo elegibles); método sin mapeo queda pendiente con motivo sin cuenta por defecto; segunda ejecución crea cero y dos simultáneas no duplican; fechas y referencias conservadas, saldos/pagos sin cambio, A no toca B; entrada con importe distinto = conflicto conservado. Dependencias: PB-ACC-003 y PB-COB-002. Reglas transversales: respetar empresa y permisos; sin partida doble, fiscal, egresos, transferencias, saldos iniciales ni reversiones; totales = entradas registradas, no saldo ni utilidad; no tocar el reporte ventas − gastos.

### Hechos encontrados
- `backend/modules/accounting/services.py` — `resolve_account`, `record_entry` (exige transacción; idempotente por `(empresa, origin_kind, origin_id)`; `EntryConflict` si difieren datos), `EntryInput` ya admite `recorded_by`, `recorded_by_name`, `origin_document_ref`, `receipt_number`.
- `backend/modules/accounting/infrastructure/django/models.py` (`EntryModel`) — unicidad `accounting_entry_origin_uniq`; sin columnas de regularización; `MethodMappingModel` guarda un único destino vigente por método, sin periodos.
- `backend/modules/accounting/domain/entry.py` — `Entry.differences` compara cuenta, moneda, monto, fecha, método, documento y comprobante; solo se inserta.
- `backend/modules/sales/infrastructure/adapters.py` (`PaymentLedgerAdapter`) y `backend/modules/receivables/infrastructure/adapters.py:58-70` — pagos nuevos crean entrada `PRODUCT`/`SERVICE` (`origin_document_ref` = id de pedido / número de fuente; Cobros pasa comprobante y autor).
- `backend/modules/sales/infrastructure/django/models.py:58-73` — `PaymentModel` de Ventas sin autor ni comprobante; `sales/domain/order.py:345-352` — un pedido cancelado conserva sus pagos; no hay estado de pago anulado en Ventas.
- `backend/modules/receivables/infrastructure/django/models.py` — pagos con `receipt_number`, `recorded_by`, `recorded_by_name`; sin estado anulado.
- `backend/modules/sales/services.py` — fachada de solo lectura de Ventas (sin pagos); `receivables` no tiene `services.py`.
- `backend/modules/sales/tests/test_boundaries.py:15-33` — mapa de dependencias; `accounting: set()` hoy.
- No existe ningún `management/commands` en el backend.
- `docs/architecture/ddd.md:1321-1325` — notas de PB-ACC-001/003 (patrón de integración y límites).

### Hipótesis / supuestos no confirmados
- «Pagos de receivables» = pagos de proformas/obligaciones de Cobros (origen `SERVICE`).
- Moneda de ambos orígenes `BOB` (única de los flujos); el informe igual agrupa por moneda.
- El «usuario de regularización» puede ser un nombre libre dado por el operador (`--executed-by`): un comando no tiene sesión de usuario.
- Interfaz = comando de servidor (la tarjeta dice «administrativo/command»); sin API ni pantalla.

### Módulos y dependencias relacionadas
`accounting` (dueño), `sales`, `receivables` (solo lectura por `services`), `shared/module_gate`.

### Implementaciones similares existentes
Adaptadores de integración `PaymentLedgerAdapter` y el de Cobros; `record_entry` idempotente; patrón de fachada `sales/services.py`.

### Comportamiento actual
Pagos anteriores a la habilitación del libro no tienen entrada y no hay forma de completarlos.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id` explícito, sin editar migraciones aplicadas, módulos solo por `services`, dominio sin Django, sin dependencias nuevas.

### Riesgos identificados
Duplicados por ejecuciones simultáneas o cruce con cobros nuevos (mitigado: bloqueo + unicidad); asignar cuenta equivocada (mitigado: mapeo explícito + previsualización); datos históricos inválidos (mitigado: error por pago).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — dinero, nueva dependencia entre módulos y migración sobre el libro.

### Diseño requerido
**NO** — sin pantallas; solo comando de servidor.

## Diseño
No aplica.

## Arquitectura
`docs/adr/ADR-conciliar-regularizar-pagos-historicos-comando-y-fuentes.md`

## Plan
`docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend `accounting`:** dominio puro `domain/regularization.py` (mapeo por rangos, clasificación faltante/existente/pendiente/conflicto/diferencia de destino/inválido, informe agrupado; INV-02, INV-03, INV-06, INV-08, AC-02, AC-03, AC-07, AC-08); caso de uso `application/regularize.py` con puertos (plan sin escritura y aplicar con bloqueo por empresa y una transacción por entrada; INV-01, INV-07, AC-04, AC-10); adaptadores `infrastructure/adapters.py` (fachadas de Ventas y Cobros, bloqueo `pg_try_advisory_lock`, `record_entry`); comando `regularize_ledger` (`--company --from --to --mapping --apply --executed-by --json`; AC-01, AC-08, AC-09); migración aditiva `0003_entry_regularization` (`regularized_at`, `regularized_by_name`; INV-04) con `EntryInput`/`Entry` y repositorio (`by_origin`).
**Fachadas:** `sales.services.list_historical_payments` (incluye pedidos cancelados; INV-05) y nuevo `receivables/services.py`.
**Pruebas:** `accounting/tests/test_regularization.py` (20: unitarias de mapeo y clasificación; integración con BD real del dataset de ambos orígenes, previsualización sin escritura, segunda pasada, campos conservados, aislamiento, conflictos, errores de uso, fallo parcial; concurrencia con hilos y carrera con un cobro nuevo). `test_boundaries` actualizado (`accounting → {sales, receivables}`, `accounting` como consumidor solo desde `adapters.py`); `ddd.md` con nota.
**Desviaciones respecto al plan:**
1. «Empresa inexistente» (AC-09) se detecta porque ninguna cuenta del mapeo le pertenece (accounting no puede importar `accounts`); sin `--mapping` en previsualización no hay validación de empresa y el informe sale vacío.
2. `--mapping` es opcional en previsualización (todo queda pendiente con motivo) y obligatorio con `--apply`.
3. El caso de uso AC-10 se prueba con un libro que rechaza una entrada (la BD no permite montos inválidos en pagos).
**Auditoría SQL de entradas regularizadas:** `SELECT origin_kind, count(*), sum(amount) FROM accounting_entry WHERE company_id = '<uuid>' AND regularized_at IS NOT NULL GROUP BY 1;`
**Deuda técnica / limitaciones:** el estado «anulado» no existe en los orígenes (se informa 0); el usuario de regularización es texto libre del operador; `.env` copiado al worktree con autorización de la persona (ignorado por git) y suite ejecutada con el venv del checkout principal.

**Verificación propia (no es el Quality Gate):** `modules.accounting` (incluye 20 nuevas), `receivables`, `modularity`, `reporting` y `sales` OK salvo 1-3 pruebas intermitentes de reloj/orden (`shared.tests.test_test_runner`, `sales.tests.test_repository`: `test_item_order_is_preserved`, `test_saves_and_loads_the_whole_aggregate`, `test_payments_are_only_appended`) que fallan igual en el checkout principal sin estos cambios (ver TASK-pruebas-intermitentes). `makemigrations --check` sin cambios.

## Review
**Veredicto: PASS** (2026-11-14, subagente aislado; sin hallazgos Critical/High).
- Backend: `modules.accounting modules.receivables modules.sales.tests.test_boundaries` → 130 tests OK (incluye las 20 nuevas); `makemigrations --check` sin cambios; `bandit` sobre `accounting`, `receivables/services.py`, `sales/services.py` sin issues.
- Límites DDD OK (dominio y aplicación sin Django/infraestructura; `accounting → sales/receivables` solo por `services` desde `adapters.py`; consultas por `company_id`; `Decimal`).
- Todos los AC-01..AC-10 con verificación; EDGE-01 y EDGE-02 solo por lectura de código.
- No verificado: suite completa en este gate (se corrió en build: solo fallan 3-4 pruebas intermitentes preexistentes, también en el checkout principal); ruff/flake8/mypy (no instalados); UI (no aplica).
- Hallazgos abiertos: Low [01](../reviews/REV-2026-11-14-conciliar-regularizar-pagos-historicos-01.md) (`classify` trata como existente una entrada con otro `origin_document_ref`, el ADR decía compararlo), Low [02](../reviews/REV-2026-11-14-conciliar-regularizar-pagos-historicos-02.md) (`regularization_stamp` es código muerto).

## Publicación
PR #71 listo para aprobación humana; no se mergea. Cambios sensibles: **base de datos** (migración aditiva `accounting/0003`) y **dinero / integración entre módulos** (ADR-conciliar-regularizar-pagos-historicos-comando-y-fuentes).
