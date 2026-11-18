# TASK-reconocer-compras-mercaderia-deuda-proveedores: Reconocer compras de mercadería y deuda con proveedores (COM-02)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-reconocer-compras-mercaderia-deuda-proveedores
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/89
**Fuente:** https://trello.com/c/tocsSz1L/19-com-02-reconocer-compras-de-mercader%C3%ADa-y-deuda-con-proveedores

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-17 | (nuevo) → INVESTIGATION | Task creado; base = `origin/accounting` (indicación de la persona), no `main` | delivery-start |
| 2026-11-17 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (lógica financiera, frontera Compras↔Contabilidad↔Inventario, reglas de recepción/reversión) | delivery-start |
| 2026-11-17 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate PASS (0 Critical/High; REV-03 Medium y REV-01/02/04 Low abiertos) | delivery-publish |
| 2026-11-17 | PUBLISH (corrección) | REV-01..04 resueltos a pedido de la persona | delivery-build |
| 2026-11-17 | PUBLISH → PLANNING → ENGINEERING | Cambio de Specification pedido y aprobado por la persona: incorporar COM-01 (asiento del pago y anticipos a proveedores); PLAN v2, ADR y DDR nuevos | delivery-start |
| 2026-11-17 | ENGINEERING → REVIEW | Implementación completa según PLAN v2; pruebas propias en verde | delivery-build |
| 2026-11-17 | REVIEW → PUBLISH | Quality Gate PASS sobre PLAN v2 (0 Critical/High; REV-05 Medium y REV-06..08 Low abiertos) | delivery-publish |
| 2026-11-18 | PUBLISH (corrección) | REV-05..07 resueltos y REV-08 aceptado y documentado, a pedido de la persona | delivery-build |

## Investigación

### Requerimiento
Tarjeta Trello COM-02 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.
- **Objetivo:** separar adquisición de inventario y pago al proveedor.
- Configuración dentro de Compras: Inventario (Activo) y Cuentas por pagar (Pasivo).
- Revisar el flujo real de confirmación/recepción y definir **un único evento** de reconocimiento; borrador o pedido al proveedor no reconocen.
- A crédito: Debe Inventario / Haber Cuentas por pagar por el importe reconocido; COM-01 liquida la deuda. Coordinar recepciones parciales y reconocimiento previo a recepción; documentar diferencias temporales y cuentas; no inventar asientos al pagar.
- Sin Gastos operativos por comprar mercadería; mantener políticas de costo e impuestos sin ampliar alcance tributario; guardado atómico e idempotente; enlace compra/recepción/asiento; preservar el corte de CONT-07.
- Aceptación: (1) compra 1.000 → Inventario Debe 1.000 / Proveedores Haber 1.000; (2) pagar 300 deja Proveedores 700 sin segundo inventario ni gasto; (3) reintentar recepción y reconocer por ambos módulos no duplica; (4) borrador no altera cuentas; fallo del asiento no deja reconocimiento parcial.
- Dependencias: CONT-12, CONT-10. Coordinación INV-01 ↔ COM-02 sobre un único evento y dueño del asiento de recepción. Transversal: API y UI, aislamiento por empresa, `Decimal`, BOB, sin conversión de divisas.

### Actualización 2026-11-17 — incorporar COM-01 (PLAN v2)
Tarjeta Trello COM-01 «Registrar pagos de compras contra cuentas por pagar» (https://trello.com/c/o5x7iTs7/7-com-01-registrar-pagos-de-compras-contra-cuentas-por-pagar), insumo: pago posterior de deuda reconocida = Debe Cuentas por pagar / Haber Caja o Banco (pagos parciales con cuentas distintas); anticipo antes de recibir como Activo «Anticipos a proveedores» aplicado al reconocer la compra; pago, pendiente y asiento atómicos y únicos, control concurrente del saldo; pagar no recibe stock ni crea gastos; mostrar asiento previsto y vínculo pago/asiento; adaptar anulaciones sin inventar reembolsos. Aceptación: deuda 1.000 pagada Caja 300 + Banco 700 → dos asientos y deuda cero; Inventario y Gastos no cambian y los reintentos no duplican; dos pagos simultáneos no exceden el saldo; falla contable revierte el pago y cuenta ajena/inactiva se rechaza; el pago de anticipos no crea gasto ni reduce deuda inexistente. Dependencias: COM-02, CONT-12, CONT-10.

**Decisiones de la persona (2026-11-17):** incluir el asiento del pago en esta tarea; anticipos a proveedores como flujo real; cuenta de salida por el método de pago (sin selector por pago); dejar de exigir la clasificación de egreso.

**Hechos nuevos (verificados en el código):**
- `RegisterPayment` solo valida el saldo, guarda el pago y la clasificación; no llama a Contabilidad y exige la clasificación de egreso cuando hay cobertura (`purchases/application/payment_commands.py:36-69`).
- Se puede pagar desde que la compra está confirmada, incluso sin recepciones (`Purchase.can_pay`, `purchase.py:338-342`); el monto no supera `total − pagado` (`purchase.py:452-461`); el bloqueo de la compra serializa pagos (`payment_commands.py:56`).
- Los métodos de Compras (`CASH, QR, BANK_TRANSFER, CARD, OTHER`, `purchases/domain/enums.py:36-42`) coinciden con los códigos de Contabilidad (`accounting/domain/catalog.py:7-9`) y el mapeo método → cuenta ya se resuelve con el rol `MONEY` (`accounting/domain/posting.py:48`).
- El catálogo tiene `PURCHASE_PAYMENT` (Debe `PAYABLE` / Haber `MONEY`) pero no hay rol de anticipos a proveedores; `Event` solo admite una segunda línea de Debe (`posting.py:52-75`) y `post_automatic_entry` solo aplica `advance_applied` a esa línea (`accounting/services.py:530-587`).
- No existen anulaciones de pagos (`PaymentRecordStatus.VOIDED` no lo produce ningún flujo) y cancelar una compra con pagos está bloqueado (`purchase.py:327-330`): no hay reembolsos que adaptar.
- Diálogo de pago y pestaña de pagos: `features/purchases/components/payment-dialog` y `purchase-payments-tab` (usa `ClassificationHintComponent` para el error de clasificación).
- El detalle de un asiento de Compras muestra el origen como código técnico «PURCHASE_RECOGNITION (módulo deshabilitado)» (observado por la persona en su entorno): la pantalla no conoce los orígenes de eventos automáticos.

**Decisiones por criterio (en ADR/PLAN v2):** el pago se reparte en deuda reconocida (`PURCHASE_PAYMENT`) y exceso (`PURCHASE_ADVANCE`); lo pagado y lo aplicado se guardan en columnas de Compras (migración aditiva) en lugar de leerse del libro; pagos sin cobertura se guardan como deuda pagada sin asiento; los pagos históricos cuentan como deuda pagada.

### Hechos encontrados
- **El catálogo ya tiene los eventos:** `PURCHASE_RECOGNITION` (Debe `INVENTORY` / Haber `PAYABLE`) y `PURCHASE_PAYMENT` (Debe `PAYABLE` / Haber `MONEY`) y los roles `INVENTORY` (Activo) y `PAYABLE` (Pasivo) (`backend/modules/accounting/domain/posting.py:45-47, 94-95`). Nadie los usa; el panel de configuración es dirigido por datos (CONT-12).
- **Fachada disponible:** `check_posting_ready`, `post_automatic_entry` (idempotente por `(empresa, evento, origin_id)`, `services.py:530-573`), `find_automatic_entry`, `automatic_entry_origins`, `reverse_automatic_entry` (`services.py:507-612`), `coverage_status` (`services.py:167`) y errores `PostingConfigurationMissing`, `FiscalPeriodClosed`, `DateOutsideFiscalPeriod`, `JournalValidationError`, `JournalConflict` (usados por Ventas en `sales/infrastructure/adapters.py:300-316`).
- **Compras no contabiliza nada hoy:** `ConfirmPurchase` (`purchases/application/purchase_commands.py:121-134`), `RegisterReception` (`receipt_commands.py:55-103`) y `RegisterPayment` (`payment_commands.py:20-69`, solo guarda la clasificación de egreso) no llaman a `accounting`. No hay llamadas a `PURCHASE_PAYMENT` fuera del catálogo (la entrada de una cuenta del libro anterior no se usa desde Compras); el pago de Compras (COM-01) aún no genera asiento.
- **Flujo real:** borrador → confirmada (`Purchase.confirm`, `purchase.py:354-366`) → recepciones parciales/completas (`Purchase.receive`, `purchase.py:381-437`, cantidad ≤ pendiente) → pagos desde confirmada (`can_pay`, `purchase.py:338-342`; el monto no supera el saldo `total − pagado`, `purchase.py:452-461`). Cancelar solo sin actividad (`can_cancel`, `purchase.py:327-330`); líneas editables solo en borrador (`ensure_editable`, `purchase.py:313-316`). Costo por línea = `quantity × unit_price` redondeado a 2 decimales (`purchase.py:110-111`).
- **Recepción:** `RegisterReception` ejecuta bajo `purchases.get(for_update=True)` (`receipt_commands.py:71`), es idempotente por `receipt_id` (`receipt_commands.py:74-78`), registra entradas de stock con modo `INVENTORY`/`DOCUMENTAL` (`receipt_commands.py:89-103`) y se ejecuta dentro de `transaction.atomic` vía `_run` (`purchase_views.py:107-110`). `RevertReception` revierte stock y estado en la misma transacción (`receipt_commands.py:125-154`).
- **Inventario:** el movimiento de entrada usa `source_type='purchase_receipt'`, `source_id=receipt.id` (`purchases/infrastructure/adapters.py:44, 63-77`); Inventario no contabiliza (no importa `accounting`).
- **Fronteras:** `ALLOWED_DEPENDENCIES['purchases'] = {accounting, catalog, inventory}` (`sales/tests/test_boundaries.py:25`); `accounting` no puede depender de `purchases` (`accounting/tests/test_coverage.py:320-324`). `purchases/infrastructure/adapters.py:100-118` ya consume `accounting_services` (clasificaciones y cobertura).
- **Cobertura/CONT-07:** `coverage_status(fecha)` decide por fecha si crear asiento (módulo deshabilitado, anterior al corte o hueco ⇒ no) (`services.py:167-178`); un asiento publicado no se revalida al reintentar (`services.py:547-555`).
- **Precedente:** VEN-01 (`TASK-contabilizar-ventas-cobros-sin-duplicar`): puerto `SalesPosting`, adaptador, 409 `posting_configuration_missing` con `issues`, enlace a la configuración en el diálogo (`sales/infrastructure/adapters.py:177-317`, `frontend/.../sales/components/delivery-dialog`).
- **Frontend de Compras:** `features/purchases/pages/{reception-form,reception-detail}` y `components/receipt-revert-dialog` (manejo de 400/409 con `ReceiptApiError`, `reception-form.component.ts:254-263`, `receipt-revert-dialog.component.ts:64-69`).

### Hipótesis / supuestos no confirmados
- El evento de reconocimiento es la **recepción** (la tarjeta descarta borrador y pedido; no dice cuál otro). Se documenta en el ADR; si la persona prefiere «al confirmar», es un cambio de Specification.
- Se reconoce también sin Inventario habilitado y para líneas sin control de stock.
- La fecha contable es la fecha de la recepción; la reversión usa la fecha de hoy (patrón de Ventas).
- (v1, reemplazado en v2) Los pagos anticipados dejaban Proveedores deudor; ahora son anticipos a proveedores.
- Las recepciones históricas no se regularizan aquí.

### Módulos y dependencias relacionadas
`purchases` (dominio, comandos, adaptador, vistas, frontend), `accounting` (solo consumo de la fachada, sin cambios previstos), `inventory` (sin cambios; fija el dueño del asiento), dependencias CONT-12/CONT-10 ya integradas en `accounting`.

### Implementaciones similares existentes
`SalesPostingAdapter` y los comandos de pedido de VEN-01; `StockEntryAdapter` (integración opcional en la misma transacción).

### Comportamiento actual
Ver «Hechos». Con Contabilidad habilitada, recibir una compra no deja rastro contable.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id`, dominio sin Django, módulos solo por `services`, sin migraciones editadas, sin dependencias nuevas, sin texto hardcodeado en frontend (es/en/pt), sin `any`.

### Riesgos identificados
Doble asiento con INV-01 (mitigado por ADR §2 y prueba de origen); recibir exige configuración con cobertura (cambio acotado); reversión bloqueada por período cerrado; recepciones históricas sin asiento; saldo deudor temporal por pagos anticipados.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — lógica financiera nueva, frontera Compras↔Contabilidad↔Inventario con decisión de dueño del asiento y cambios de reglas de recepción/reversión.

### Diseño requerido
**SI** — rechazos accionables y enlace al asiento en recepción y reversión (sin pantallas nuevas).

## Diseño
`docs/design/DDR-reconocer-compras-mercaderia-deuda-proveedores-errores-accionables-y-asiento-en-recepcion.md`
`docs/design/DDR-reconocer-compras-mercaderia-deuda-proveedores-dialogo-de-pago-asiento-previsto-y-vinculo.md` (v2)

## Arquitectura
`docs/adr/ADR-reconocer-compras-mercaderia-deuda-proveedores-evento-recepcion-y-asiento.md` (decisión 7 reemplazada)
`docs/adr/ADR-reconocer-compras-mercaderia-deuda-proveedores-pagos-y-anticipos-a-proveedores.md` (v2)

## Plan
`docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md` (v2, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según **PLAN v1**, sin cambios de Specification.

- **Dominio** (INV-01/04): `Purchase.receipt_amount(receipt, received_before)` valora lo recibido como diferencia del subtotal acumulado por línea (sin deriva de redondeo entre recepciones parciales); `PostingRejected(code, message, extra)`.
- **Puerto y adaptador** (AC-05..AC-09, INV-02/03): `PurchasePosting` en `purchases/application/ports.py` y `PurchasePostingAdapter` en `purchases/infrastructure/adapters.py` (solo `accounting.services`: `post_automatic_entry`, `reverse_automatic_entry`, `find_automatic_entry`); traduce `PostingConfigurationMissing`, período cerrado/fuera de períodos y rechazos del motor.
- **Comandos** (AC-01..AC-05, AC-07): `RegisterReception` publica `PURCHASE_RECOGNITION` (`origin_id` = recepción, fecha = fecha de la recepción) tras guardar recepción y stock, sin publicar en reintentos ni con importe 0; `RevertReception` revierte el asiento antes de marcar la recepción revertida.
- **API** (API-01/02, AC-08): 409 `posting_configuration_missing` (con `issues`) / `fiscal_period_unavailable` / `ledger_rejected` / `ledger_conflict` vía `_run`; el detalle de la recepción añade `accounting_entry` y `accounting_enabled`.
- **Frontend** (UI-01..03, AC-10): formulario de recepción con alerta de faltantes y enlace a Compras › Asientos automáticos; el diálogo de reversión ya mostraba el mensaje del 409; detalle con fila «Asiento contable» (enlace a `/pocketbiz/accounting/journal/:id` o «Sin asiento contable»); claves es/en/pt. Pantallas de referencia: las existentes de Compras y la alerta de VEN-01 (estilo tenue de Contabilidad, SCSS vía `@use` del parcial de Contabilidad en `reception-form.component.scss`); componentes compartidos: `MoneyPipe`.
- **Pruebas:** `purchases/tests/test_purchase_posting.py` (17: AC-01..AC-09 con Contabilidad real) y specs de recepción (formulario, detalle, servicio).

**Desviaciones respecto al plan:** (1) v1 no escribió pruebas con hilos propias; v2 las agrega (ver «Pruebas de concurrencia» abajo). (2) El diálogo de reversión no necesitó cambios de código: ya muestra `err.message` de los 409.

**Deuda técnica / pendiente:** los mensajes de `issues` llegan solo en español (deuda ya declarada en CONT-12); el SCSS del aviso se repite entre Ventas y Compras (candidato a `shared/`); la reversión usa la fecha de hoy.

**Verificación propia (no es el Quality Gate):** backend `manage.py test` 2052 OK, `makemigrations --check` sin cambios; frontend `ng lint` OK, `i18n:check` 2184 claves y 0 faltantes, `ng test` 1598 OK, `ng build` OK. Pruebas corridas con el `.venv` del checkout principal y un `.env` copiado (no versionado) con base de pruebas `test_com02`.

### Implementación v2 (PLAN v2: COM-01 incorporado)
Implementado según **PLAN v2**, sin cambios adicionales de Specification.

- **Contabilidad** (`accounting/domain/posting.py`, `services.py`; AC-15..19, AC-17): rol `SUPPLIER_ADVANCES` (Activo), evento `PURCHASE_ADVANCE` y segunda línea de Haber (`Event.extra_credit_role`) en `PURCHASE_RECOGNITION`; `post_automatic_entry` generaliza `advance_applied` a Debe o Haber (sin líneas de importe cero, cuentas solo si la línea existe); fachada nueva `preview_automatic_entry` y `automatic_entries_for` (+ `DjangoJournalRepository.by_origins`); `origin.label/module` del evento en el serializer de asientos (API-05).
- **Compras, dominio y datos** (INV-06..09, AC-21): `split_payment` (deuda/anticipo), `Purchase.received_value`, `Payment.debt_amount/advance_amount` + `allocate`, `Receipt.advance_applied`; migración aditiva `purchases/0009_payment_advances` (los pagos existentes pasan a `debt_amount = amount`); repositorios con `debt_paid_total`, `advance_total`, `advance_applied_total`.
- **Compras, aplicación** (AC-11..16, 20): `RegisterPayment` (reparto, asientos `PURCHASE_PAYMENT`/`PURCHASE_ADVANCE` atómicos, clasificación opcional que ya no bloquea) y `RegisterReception` (aplica anticipos pendientes al reconocer); `PreviewPayment`; puerto y adaptador ampliados (`covers`, `record_payment`, `preview_payment`, `payment_entries`).
- **API** (API-03/04): `GET /api/purchases/{id}/payments/preview/` y campos `debt_amount`, `advance_amount`, `accounting_entries` en pagos.
- **Frontend** (UI-04..06): diálogo de pago con «Asiento previsto» y alerta accionable, pestaña de pagos con enlaces a los asientos y marca de anticipo, Movimientos muestra la etiqueta del evento; claves es/en/pt (incluye rol y evento en el panel de configuración); `track $index` en las líneas del panel (había claves duplicadas con eventos de dos líneas del mismo lado).
- **Pruebas:** `purchases/tests/test_payment_posting.py` (19, con hilos y Contabilidad real), `payment_support.py`, `accounting/tests/test_supplier_advances.py` (11), unit de reparto en `test_purchase_posting_unit.py`; ajustadas las pruebas de clasificación (`test_payment_classification_api.py`), de campos de pago y de catálogo; specs de payment-dialog, purchase-payments-tab, payments-api.service y journal-detail.

**Desviaciones respecto al plan:** (1) la migración es `0009` (ya existía `0008_payment_classification`); ADR y PLAN corregidos. (2) La columna «Asiento contable» de la pestaña de pagos se muestra cuando algún pago tiene asiento (la API de pagos no expone si Contabilidad está habilitada); los pagos sin asiento de esa lista dicen «Sin asiento contable». (3) El diálogo de pago ya no usa `ClassificationHintComponent` (el error de clasificación no existe más).

**Deuda técnica / pendiente:** el SCSS de aviso sigue duplicado entre Ventas y Compras; la clasificación de egreso de pagos queda sin uso obligatorio (candidata a retiro); los pagos anteriores al corte con compras recibidas después no se reflejan en el libro (ADR §10); `PaymentClassificationError` y sus constantes quedaron sin uso.

**Verificación propia (no es el Quality Gate):** backend `manage.py test` 2104 OK, `makemigrations --check` sin cambios; frontend `ng lint` OK, `i18n:check` 2197 claves y 0 faltantes, `ng test` 1606 OK, `ng build` OK.

### Pruebas de concurrencia (agregadas después del Quality Gate final)
`purchases/tests/test_posting_concurrency.py` (hilos reales sobre PostgreSQL, Contabilidad e Inventario reales; el primer hilo retiene el bloqueo de la compra y el segundo intenta entrar; se verifica el resultado final):
- **Pago y recepción a la vez** sobre la misma compra, en los dos órdenes (AC-13, AC-16): en ambos el libro queda igual (sin deuda, 100 de anticipo sin aplicar, Inventario 400, Caja 500) y `debt_amount + advance_amount = amount`.
- **Mismo `payment_id` enviado dos veces a la vez** (AC-12): un solo pago, un solo asiento, un hilo `created=True` y el otro `False`, sin error.
- **Mismo `receipt_id` enviado dos veces a la vez** (AC-04): una recepción, un asiento de reconocimiento, un movimiento de stock.
- **Validación por mutación:** se comprobó (fuera del repo) que, sin el bloqueo de fila de la compra, las cuatro pruebas fallan; con él, pasan. Hallazgo de método: al principio dos de ellas pasaban sin el bloqueo porque el primer uso de la cobertura (alta del corte) serializaba a los hilos por casualidad; ahora el corte se fija en `setUp`.
Verificación propia: backend 2170 pruebas OK, `ruff`/`flake8` sin avisos en el archivo nuevo.

## Review
**Quality Gate (PLAN v1): PASS** (subagente aislado, 2026-11-17). Backend: `manage.py test` 2052 OK, `makemigrations --check` sin cambios, bandit sin hallazgos, 0 líneas nuevas >120 caracteres. Frontend: `npm run lint` OK, `i18n:check` 2184 claves y 0 faltantes, `ng test` 1598 de 1598 OK, `ng build` OK. `ruff`/`flake8` solo con avisos de estilo (no comparados con la base); `mypy` y `npm audit` no ejecutados. Fronteras DDD, orden transaccional, AC-01..AC-09, INV, API y UI verificados. **Revisión visual: no verificada** (no se levantó la aplicación con sesión).
Hallazgos (ninguno Critical/High); **todos resueltos después del Gate** (ver Resolution en cada REV; verificación propia: backend 2071 pruebas OK, `makemigrations --check` sin cambios; el Gate no se repitió):
- [REV-01](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-01.md) Low: deriva de 1 centavo al revertir una recepción intermedia y volver a recibir con importes que redondean.
- [REV-02](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-02.md) Low: revertir con Contabilidad deshabilitada hoy deja vivo el asiento de una recepción contabilizada antes.
- [REV-03](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-03.md) Medium: faltan pruebas de la Test Specification (unit de `receipt_amount`, comandos con puerto falso, serializer, `RevertStockShortage`, `ledger_*`, `in_gap`).
- [REV-04](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-04.md) Low: el TASK decía «SCSS copiado» pero el componente hace `@use` del parcial de Contabilidad (corregido en este TASK).

**Quality Gate (PLAN v2): PASS** (subagente aislado, 2026-11-17). Backend: `manage.py test` 2104 OK, `makemigrations --check` sin cambios, bandit sin hallazgos; migración `0009` verificada reversible; prueba temporal de conservación con 25 semillas aleatorias (recibir/pagar/revertir) OK. Frontend: `npm run lint` OK, `i18n:check` 2197 claves y 0 faltantes, `ng test` 1606 de 1606 OK, `ng build` OK; `npm audit` 3 altas preexistentes en `@angular/localize` (el diff no agrega dependencias); `ruff` con configuración ad hoc solo con avisos de estilo; mypy/flake8 no ejecutados. Reparto deuda/anticipo bajo el bloqueo de la compra, idempotencia por evento, vista previa sin escritura y fronteras DDD verificados. **Revisión visual: no verificada.**
Hallazgos de v2 (ninguno Critical/High); **corregidos después del Gate** (2026-11-18, ver Resolution en cada REV; verificación propia: backend 2166 pruebas OK, `ruff` y `flake8` sin avisos en lo cambiado, frontend lint/i18n/build/tests OK; el Gate no se repitió):
- [REV-05](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-05.md) Medium: las alertas del diálogo de pago usan el naranja con texto blanco de la plantilla (sin el parcial `alert-warning` del DDR); contraste AA no cumplido según el código.
- [REV-06](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-06.md) Low: el diálogo se aparta del DDR (botón no se deshabilita con faltantes previstos, `issues` de la vista previa sin enlace, fallo de la vista previa tragado, aviso de carga no accesible, `sideLabels` sin uso).
- [REV-07](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-07.md) Low: higiene de lint en Python nuevo (líneas largas, imports sin uso).
- [REV-08](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-08.md) Low, SPECIFICATION: el reparto cuenta como deuda reconocida también recepciones sin asiento (históricas o previas al corte); un pago posterior puede dejar Cuentas por pagar deudor. **Aceptado y documentado** (ADR de pagos §11).

**Quality Gate final (estado completo v1 + v2 + correcciones + dos merges de `accounting`): PASS** (subagente aislado, 2026-11-18). Backend: `manage.py test` 2166 OK, `makemigrations --check` sin cambios, `sqlmigrate purchases 0009 --backwards` reversible, `ruff` y `flake8` sin avisos en lo cambiado, bandit sin hallazgos. Frontend: `npm run lint` OK, `i18n:check` 2223 claves y 0 faltantes, `ng test` 1626 de 1626 OK, `ng build` OK; sin `float`, sin `any`, sin texto hardcodeado en lo nuevo. Verificó de forma independiente REV-05..08 y la conservación contable (pagar, recibir, anticipos, reversión). `npm audit`, `mypy` y una migración real hacia atrás sobre datos no se ejecutaron. Hallazgos nuevos (ambos Low, **resueltos**): [REV-09](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-09.md) (API-03 vs `account` solo con `name`) y [REV-10](../reviews/REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-10.md) (textos de v1 desactualizados).

**Revisión visual (2026-11-18, navegador integrado sobre una base y servidores temporales; escritorio 1440 px y móvil 375 px):** el diálogo de pago muestra el asiento previsto (anticipo, líneas Debe/Haber con nombres de cuenta); tras pagar, la pestaña Pagos muestra «Incluye anticipo» y el enlace «Asiento de anticipo»; el detalle del asiento muestra el Origen como «Pagar por adelantado a un proveedor»; el detalle de la recepción muestra la fila «Asiento contable» con enlace. Con el rol de anticipos sin configurar, el diálogo muestra la alerta con el enlace a la configuración, contraste 7,21:1 (claro y oscuro) y Registrar deshabilitado; el formulario de recepción sin Inventario ni Anticipos configurados muestra la alerta con contraste 9,46:1. En móvil no hay desbordamiento horizontal y el diálogo cabe en pantalla. Límites: el tema oscuro se probó con la clase del `body`, no con el conmutador real; no se probó tablet.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/89 (base `accounting`) listo para aprobación humana; no se mergea. Incluye ADR (reconocer al recibir) y cambia reglas de recepción/reversión con cobertura contable: lo aprueba una persona. Migración aditiva `purchases/0009_payment_advances` (v2). Pendientes: `npm audit` y `mypy` no ejecutados; revisión visual solo en escritorio y móvil con el tema oscuro por clase, mypy y npm audit no realizados.
