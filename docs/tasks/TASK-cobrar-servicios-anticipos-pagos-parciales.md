# TASK-cobrar-servicios-anticipos-pagos-parciales: PB-COB-001 · Cobrar servicios con anticipos y pagos parciales

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-cobrar-servicios-anticipos-pagos-parciales (desde `origin/main` c82d9a7, que ya contiene PB-COT-001/002 tras el PR #60)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/61
**Fuente:** https://trello.com/c/P070M244/8-pb-cob-001-cobrar-servicios-con-anticipos-y-pagos-parciales

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado desde tarjeta de Trello | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE, diseño SI; decisiones de negocio resueltas con el usuario | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Specification READY, PLAN v1 y PR | delivery-start |

## Investigación

### Requerimiento
Fuente: tarjeta de Trello «PB-COB-001 · Cobrar servicios con anticipos y pagos parciales» (orden 8 de 16, P1; dependencia obligatoria PB-COT-002). Resumen fiel (insumo, **no** Specification aprobada):
- **Historia:** como responsable de caja, cobrar tratamientos aceptados con anticipos y abonos para conocer el saldo real sin duplicar ventas ni ingresos.
- **Menú/vistas:** flujo financiero actual → Cobros, con acceso desde la proforma y la ficha administrativa del paciente; detalle de obligación con tratamientos aceptados, pagos, imputaciones y saldo; filtros por cliente, fecha y estado de pago.
- **Campos:** cliente, origen y versión/línea aceptada; obligación única; importe acordado por línea; pago con fecha, monto > 0, método activo, referencia opcional, usuario; distribución por línea (y profesional «cuando corresponda»); total cobrado y saldo.
- **Reglas:** reutilizar el contrato de Ventas/Cobros tras inspeccionar el código; solo importes aceptados; una sola obligación por compromiso (no duplicar al versionar); suma de imputaciones = pago, sin superar saldo de línea ni de obligación; saldo = aceptado exigible − pagos válidos imputados; reintentos idempotentes; pagos concurrentes no sobrepagan; sin consumo de stock; correcciones por el flujo financiero disponible o fuera de alcance.
- **Interfaz:** mostrar propuesto, aceptado, cobrado y saldo; distribución explícita por tratamiento; resumen antes de confirmar; comprobante/referencia y saldo actualizado tras el éxito; sin diagnósticos a caja.
- **Aceptación:** aceptado 300 → anticipo 100 deja 200 → abono 50 deja 150; doble envío no duplica; dos pagos concurrentes sobre saldo 150 no suman más de 150; rechazados no son cobrables.
- **Límites:** un consultorio por empresa; sin Sucursales ni reserva de recursos; honorarios y ejecución no bloquean cobrar anticipos.

Aclaraciones del usuario (2026-11-04): (1) la rama base es `main` (las proformas ya se integraron con el PR #60); (2) **se cobran ambas** proformas, la genérica (`quotations`) y la odontológica (`dentistry`); (3) **no se puede rectificar a «rechazada» una línea con importe cobrado**; (4) **método de pago = enum existente de Ventas**, todos activos, sin catálogo configurable.

### Hechos encontrados
- `backend/modules/quotations/domain/proforma.py:135-170` — `Proforma` con `totals` (propuesto/aceptado/pendiente/rechazado), `acceptance_status` y líneas con `current_decision`; `subtotal = money(cantidad × precio)` (`:87-89`).
- `quotations/domain/proforma.py:206-230` — `_classify`: las líneas aceptadas heredadas no se pueden editar ni quitar; la versión nueva copia líneas con `id` nuevo y `origin_line_id` (`:244-251`), y la decisión vigente se copia como `carried`.
- `quotations/domain/proforma.py:279-297` — `rectify` permite pasar de aceptada a rechazada con motivo; hoy no conoce cobros.
- `backend/modules/dentistry/domain/proforma.py:156-300` — `DentalProforma` copia adaptada con las mismas decisiones/versiones y numeración propia `ODO-NNNNNN` (`docs/adr/ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia.md`); el módulo genérico **no** se toca desde Odontología.
- `quotations/application/proformas.py:140-181` — patrón de idempotencia: `idempotency_key` UUID en el cuerpo (`api/serializers.py:31`), hash del contenido y 409 si se reusa con otros datos; `infrastructure/django/models.py:90-102` — tabla de lotes con único `(company_id, idempotency_key)`; `repositories.py:37-39,75` — `select_for_update` en cabecera y contador.
- `backend/modules/sales/domain/order.py:152-159,348-365` — `Payment` y `register_payment` (monto > 0, método enum, fecha no futura, referencia ≤ 100, monto ≤ saldo); `sales/domain/enums.py:34-40` — `PaymentMethod` = CASH, QR, BANK_TRANSFER, CARD, OTHER.
- `sales/infrastructure/django/models.py:7-73` — `Order` exige `OrderItem.product_id` y cantidades enteras, `Payment` sin imputaciones ni clave de idempotencia; no hay catálogo de métodos activos, ni reversión/anulación de pagos (`docs/producto/modulos-implementados.md:179`).
- `backend/modules/modularity/domain/modules.py:20-37` — catálogo de módulos; `quotations` requiere `services`+`customers`, `dentistry` requiere `customers`; los módulos nuevos se registran aquí.
- `backend/modules/sales/tests/test_boundaries.py:12-30` — `ALLOWED_DEPENDENCIES` y `CONSUMERS`: un módulo nuevo debe declararse y consumir a otros solo por `modules.<otro>.services` desde `infrastructure/adapters.py`.
- `quotations/api/views.py:21,54-56` y `dentistry/api/proforma_views.py:26` — `required_modules` por vista y política `can_rectify` solo para `admin`; `accounts/models.py:32-34` — único rol `admin`.
- Frontend: `features/quotations/pages/proforma-detail.component.*`, `features/dentistry/pages/dental-proforma-detail.component.*`, `features/dentistry/pages/patient-detail.component.*`; rutas en `app/app.routes.ts:54-…`; plantillas de pantalla del sistema de diseño en `docs/design/design-system.md` §5 («Detalle con selección de líneas y registro de decisión», «Formulario con líneas y paso de resumen», «Lista de solo lectura con filtros»).

### Hipótesis / supuestos no confirmados
- «Profesional por línea»: las líneas de proforma no tienen profesional; la distribución por profesional queda fuera (el pago se imputa por línea). Honorarios son otra tarea (la tarjeta dice que no bloquean).
- «Usuario de la empresa»: se registra el usuario autenticado que cobra; no hay rol de caja (solo `admin`), así que cobrar exige el mismo permiso que usar la proforma.
- Reporting no incluye todavía ingresos de servicios; esta tarea no los agrega (no hay duplicación porque Cobros no crea pedidos de Ventas).

### Módulos y dependencias relacionadas
`quotations`, `dentistry` (fuentes del compromiso), `customers` (identidad), `modularity` (catálogo de módulos), `sales` (solo como referencia de contrato), frontend `quotations`, `dentistry`, nuevo `receivables`.

### Implementaciones similares existentes
Pagos de Ventas y Compras (saldo = total − pagado, monto ≤ saldo); libro de decisiones idempotente de COT-002; contador por empresa con bloqueo.

### Comportamiento actual
Se puede presentar, aceptar y versionar proformas, pero no cobrarlas. Ventas cobra solo pedidos de productos. No existe nada que relacione una línea aceptada con dinero.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id`, no editar migraciones aplicadas, módulos solo por fachada, sin dependencias nuevas, sin texto hardcodeado (i18n es/en/pt), `docs/architecture/ddd.md`.

### Riesgos identificados
- Carrera entre cobrar y rectificar/versionar la misma proforma (mitigada con bloqueo de filas y marca «con cobro» en la línea de origen).
- Dos fuentes de proforma con la misma semántica (duplicación ya aceptada por ADR de COT odontológico).
- Líneas con importes que cambian al versionar (aceptadas heredadas son inmutables, ver `_classify`).
- Sin reversión: un cobro erróneo no se puede corregir en esta tarea.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — módulo nuevo (`receivables`), integración con dos módulos fuente, tabla de pagos con imputaciones, idempotencia y concurrencia, cambio de regla en dos agregados existentes y alta en el catálogo de módulos.

### Diseño requerido
**SI** — pantallas nuevas (lista de cobros, detalle de obligación, formulario de pago con distribución y resumen) y accesos desde proforma y ficha del paciente.

## Diseño
DDR: `docs/design/DDR-cobrar-servicios-anticipos-pagos-parciales-pantallas-cobros.md`.

## Arquitectura
- `docs/adr/ADR-cobrar-servicios-anticipos-pagos-parciales-modulo-cobros-y-fuentes.md`
- `docs/adr/ADR-cobrar-servicios-anticipos-pagos-parciales-pagos-idempotencia-y-concurrencia.md`

## Plan
`docs/plans/PLAN-2026-11-04-cobrar-servicios-anticipos-pagos-parciales.md` (v1, COMPLETO). Specification readiness: **READY**.

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
