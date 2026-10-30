# TASK-compras-registrar-pagos-saldo: Registrar pagos y saldo de compras (PB-COM-005)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-compras-registrar-pagos-saldo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/38
**Fuente:** https://trello.com/c/B13dklNF/19-pb-com-005-registrar-pagos-y-saldo-de-compras

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-10-30 | INVESTIGATION → DESIGN | Veredicto NEEDS_ARCHITECTURE; diseño requerido | delivery-start |
| 2026-10-30 | DESIGN → ARCHITECTURE | DDR escrito | delivery-start |
| 2026-10-30 | ARCHITECTURE → PLANNING | ADR escrito | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación y pruebas escritas | delivery-build |

## Investigación

### Requerimiento
Fuente: https://trello.com/c/B13dklNF (tarjeta «PB-COM-005 · Registrar pagos y saldo de compras», módulo Compras, P1, dependencia PB-COM-003). El contenido de la tarjeta es **insumo**, no una Specification aprobada.

Historia: como administrador, quiero registrar pagos parciales o completos para conocer cuánto debo a mis proveedores.

- **Acceso y vistas:** detalle de Compra → pestaña «Pagos» → «Registrar pago»; diálogo/formulario de pago y tabla de pagos. Sin menú independiente de pagos.
- **Resumen visible:** total de la compra, total pagado, saldo y estado de pago. **Tabla:** fecha, referencia interna, monto, método y usuario que registró.
- **Formulario:** fecha obligatoria, monto > 0 y método obligatorio (efectivo, QR, transferencia, tarjeta u otro, «según configuración disponible»). Muestra el saldo actual junto al monto.
- **Acciones:** «Registrar pago» solo con saldo y documento confirmado; confirmar o cancelar el formulario. Con saldo cero se muestra «Pagado» y se deshabilita el alta.
- **Interfaz:** bloquear sobrepago y conservar el formulario ante error; una compra pendiente de recibir puede pagarse. No ofrecer borrar pagos confirmados, reembolso ni cobro automático por QR.
- **AC de la tarjeta:** (1) cada pago guarda monto positivo, fecha y método (efectivo, QR, transferencia, tarjeta, otro); (2) saldo y estado pendiente/parcial/pagado se calculan desde pagos confirmados y el MVP bloquea sobrepagos incluso con solicitudes simultáneas; (3) se puede pagar antes o después de recibir; pagar no modifica inventario ni crea un gasto automático.
- Sin checklists ni comentarios en la tarjeta. Enlaces a documentos de Google (historias y especificaciones comunes) no consultados: no están accesibles desde el conector.

### Hechos encontrados
- PB-COM-003 y PB-COM-004 están en `main` (`e4948d8`). El agregado ya tiene `payment_status: PaymentStatus` (`unpaid|partial|paid`), sin escritor (`backend/modules/purchases/domain/enums.py:15-18`, `domain/purchase.py` campo `payment_status`); la columna existe en `purchases_purchase` (`infrastructure/django/models.py:41`) y el mapper la lee y escribe (`infrastructure/django/mappers.py:53,69`).
- La cancelación ya se bloquea con actividad de pago: `has_activity` considera `payment_status != UNPAID` (`domain/purchase.py`, propiedades `has_activity`/`can_cancel`); `allowed_actions` hoy incluye `receive` y `cancel` (propiedad `allowed_actions`). Falta la acción `pay`.
- El detalle del frontend ya expone `paymentStatus` y las etiquetas `PAYMENT_STATUS_LABELS` («Sin pagar», «Pago parcial», «Pagada») (`frontend/panel_admin/src/app/features/purchases/models/purchase.ts:33-37`).
- No existen pagos de compra: ni tabla, ni entidad, ni endpoints. Migración más reciente de Compras: `0005_receipt_inventory_mode`.
- Patrón idéntico ya resuelto en Recepciones: entidad hija inmutable con `id` provisto por el cliente (idempotencia), repositorio con inserción atómica y `ReceiptConflict`, bloqueo de la compra con `get(for_update=True)`, acumulado leído tras el bloqueo (`application/receipt_commands.py`, `RegisterReception.execute`), referencia provisional derivada del id (`domain/receipt.py`, `reference`), tabla sin FK entre agregados (`models.py`, `ReceiptModel`), vistas con `_run` que traduce excepciones (`api/purchase_views.py`, `_run`) y rutas anidadas (`api/purchase_urls.py`).
- Cobro de Ventas como referencia de reglas: `Order.register_payment` valida monto positivo, método, fecha no futura y `amount <= balance` (`backend/modules/sales/domain/order.py`, `register_payment`), con `CheckConstraint(amount>0)` en `sales_payment` (`sales/infrastructure/django/models.py:59-72`). Sus enums de método se copian por módulo («mismos códigos… propios de este módulo», `expenses/domain/enums.py:11-18`).
- Métodos de pago y etiquetas ya definidos para el sistema: `PAYMENT_METHODS` (`modularity/domain/settings.py:23-25`). La única configuración de método es `sales.default_payment_method` (módulo Ventas); no existe una de Compras.
- Dinero: `shared/domain/money.py` (`parse_money`, `MONEY_MAX`, hasta 2 decimales, rechaza `float`).
- Frontend: detalle con pestañas simples `Resumen`/`Recepciones` y acciones por `allowed_actions` (`purchase-detail.component.html:21-40`); diálogos `NgbModal` (`components/purchase-cancel-dialog`); pestaña de documentos relacionados (`components/purchase-receipts-tab`); servicio `receipts-api.service.ts`. Pantalla de referencia de pagos en Ventas: `features/sales/components/order-payments`.
- El documento DDD y `test_boundaries` no cambian: esta task no agrega dependencias entre módulos (`sales/tests/test_boundaries.py:17`).

### Hipótesis / supuestos no confirmados
Reversibles con aprobación del usuario; ninguno bloquea:
- **H-01** Referencia de pago provisional derivada del id: `PAG-` + 8 hex mayúsculos (como `COM-`/`REC-`); la numeración correlativa es otra task.
- **H-02** Métodos: los cinco códigos fijos `CASH, QR, BANK_TRANSFER, CARD, OTHER`. «Según configuración disponible» se interpreta como la lista existente; no se crea una configuración de Compras ni se reutiliza la de Ventas (los módulos no se acoplan). Sin método sugerido: la persona elige.
- **H-03** Fecha del pago: obligatoria, válida y no futura (igual que Ventas y Recepciones); por defecto hoy en la interfaz. Sin cota inferior.
- **H-04** Solo se paga una compra `confirmed` con saldo > 0; en borrador o cancelada → 409. Pagar es independiente del estado de recepción.
- **H-05** El pago es inmutable. Existe `status` (`confirmed`) para que el saldo se calcule «desde pagos confirmados», pero no hay acción de anular, borrar ni reembolsar en esta task (queda como deuda).
- **H-06** Idempotencia: el cliente envía `payment_id` (UUID generado al abrir el diálogo); repetir devuelve el pago ya registrado sin duplicar.
- **H-07** Sin referencia externa ni notas en el pago (no pedidas).
- **H-08** Saldo = total − suma de pagos confirmados; el estado de pago se persiste en `payment_status` (`unpaid` sin pagos, `partial` con 0 < pagado < total, `paid` con pagado = total) y lo recalcula `Purchase.register_payment`.
- **H-09** Una compra confirmada con total 0,00 tiene saldo 0: no admite pagos, la interfaz dice «Sin saldo por pagar» y el estado sigue `unpaid` (marcarla `paid` bloquearía su cancelación por `has_activity`).
- **H-10** Una vez con pagos, la compra no puede cancelarse (regla ya vigente de PB-COM-003).

### Módulos y dependencias relacionadas
Compras (propietario). Sin Inventario, Gastos ni Catálogo: pagar no cambia existencias ni crea gastos. `modularity.module_gate` y `required_modules=('purchases',)` por las vistas existentes.

### Implementaciones similares existentes
Recepciones de Compras (entidad hija, idempotencia, bloqueo, pestaña); cobros de Ventas (reglas de pago y sobrepago); diálogos `NgbModal` de confirmar/cancelar compra.

### Comportamiento actual
No se puede registrar un pago. El detalle de una compra confirmada muestra «Sin pagar» y, en su barra de acciones, el pago no existe como acción. `payment_status` nunca cambia.

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, dinero en `Decimal`, no editar migraciones aplicadas, dominio sin Django, estados por métodos del agregado, Reactive Forms, tipos explícitos, sin dependencias nuevas. Sistema de diseño de `docs/design/design-system.md`.

### Riesgos identificados
- Sobrepago por solicitudes simultáneas: mitigado con el bloqueo de la compra y el acumulado leído tras el bloqueo (verificación con PostgreSQL real).
- Doble envío del diálogo: `payment_id` idempotente.
- Cambio de dinero en datos reales: migración aditiva, sin tocar compras existentes (`payment_status` ya es `unpaid`).
- Compras confirmadas con total 0 (H-09).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — lógica financiera nueva (saldo, sobrepago, concurrencia), nueva tabla con migración y contrato API nuevo. No cruza módulos, por lo que basta un solo ADR.

### Diseño requerido
**SI** — pestaña nueva «Pagos», diálogo de alta con saldo visible y estados de error que conservan lo escrito.

## Diseño
`docs/design/DDR-compras-registrar-pagos-saldo-pestana-y-dialogo-pago.md` (Propuesto). Sin componente compartido nuevo.

## Arquitectura
`docs/adr/ADR-compras-registrar-pagos-saldo-modelo-saldo-y-contrato.md` (Propuesto).

## Plan
`docs/plans/PLAN-2026-10-30-compras-registrar-pagos-saldo.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
**Backend** (`backend/modules/purchases/`): `domain/payment.py`, `PaymentMethod`/`PaymentRecordStatus`, `Purchase.register_payment`/`can_pay`/`pay` en `allowed_actions`, `PurchaseNotPayable`, `PaymentConflict` (INV-01…07, 11; AC-01…06, 09); `infrastructure/django/{models,mappers,payment_repository}.py` y migración `0006_payments` con `CheckConstraint(amount > 0)` (AC-14); `application/payment_commands.py` (`RegisterPayment`: bloqueo de la compra, acumulado tras el bloqueo, idempotencia por `payment_id`; INV-08, 09; AC-08, 13), `payment_queries.py` (`ListPayments`) y `GetPurchase` con `paid_total`/`balance` (AC-10, 11); `api/payment_{views,serializers}.py`, ruta `payments/` y campos nuevos del detalle (AC-01…AC-12). Sin dependencias nuevas entre módulos (INV-10, AC-07).
**Frontend** (`features/purchases/`): `models/payment.ts`, `services/{payments-api.service,payment-amounts}.ts`, componentes `purchase-payments-tab` y `payment-dialog` (el diálogo hace la llamada y conserva lo escrito ante errores), pestaña «Pagos» en `purchase-detail` con `?tab=payments`, Total pagado/Saldo y badge en el Resumen, botón «Registrar pago» según `pay` (AC-15…AC-20). Pantalla de referencia: «Detalle con pestañas y acciones de ciclo de vida» (`purchase-detail`, `purchase-receipts-tab`) y `purchase-cancel-dialog`; sin componente compartido nuevo.
**Docs:** `modulos-implementados.md` (§3.12), `ddd.md` (nota de pagos), `design-system.md` (patrón «pestaña con resumen y alta por diálogo»).
**Pruebas escritas:** `test_payment_{domain,application,api,repository,concurrency}.py`; specs Karma de servicio, importes, diálogo, pestaña y detalle. Se ajustaron aserciones existentes de `allowed_actions` (ahora incluyen `pay`) y `DETAIL_FIELDS` (`paid_total`, `balance`).
**Verificación local (no es el Quality Gate):** dominio/aplicación/API/repositorio de Compras y guardas pasan con SQLite en memoria (sin credenciales de PostgreSQL); `makemigrations --check` sin cambios; `ng lint` OK; `ng build` OK; Karma de `features/purchases` + `features/inventory` (321) OK con `app.component.spec.ts` apartado temporalmente (falla al compilar en `main` por `title`, ajeno a esta task; restaurado). **No ejecutado:** pruebas con PostgreSQL real (incluye `test_payment_concurrency`, AC-13) ni revisión visual. Con SQLite fallan 5 pruebas de concurrencia ya existentes que requieren PostgreSQL.
**Desviaciones del plan:** ninguna de alcance. Detalle menor: el botón «Registrar pago» de la barra de acciones del Resumen cambia a la pestaña «Pagos» (el alta vive en la pestaña, según el DDR). Se añadió la clase `col-grey` para «Sin pagar» (badge sin color de estado fuerte).
**Deuda:** anular/reembolsar pagos (estado `voided` reservado, sin acción, H-05); numeración correlativa de `PAG-`; la fecha futura se valida con la hora local del servidor.

## Review
_Pendiente_

## Publicación
_Pendiente_
