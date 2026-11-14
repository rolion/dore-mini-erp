# TASK-conciliar-regularizar-pagos-historicos: Conciliar y regularizar pagos históricos de productos y servicios (PB-ACC-004)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-conciliar-regularizar-pagos-historicos
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/17DwVe39/21-pb-acc-004-conciliar-y-regularizar-pagos-hist%C3%B3ricos-de-productos-y-servicios

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-14 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (f45b0cd, incluye PB-ACC-003 y PB-COB-002) | delivery-start |
| 2026-11-14 | INVESTIGATION → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (dinero, nueva dependencia accounting → sales/receivables, migración); sin UI | delivery-start |
| 2026-11-14 | PLANNING → ENGINEERING | Specification READY: la tarjeta fija las reglas; las decisiones técnicas están en el ADR | delivery-start |

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
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
