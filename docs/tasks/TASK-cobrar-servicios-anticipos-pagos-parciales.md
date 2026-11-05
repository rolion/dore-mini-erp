# TASK-cobrar-servicios-anticipos-pagos-parciales: PB-COB-001 · Cobrar servicios con anticipos y pagos parciales

**Etapa actual:** PUBLISH
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
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa; pendiente Quality Gate | delivery-build |
| 2026-11-04 | REVIEW → PUBLISH | Quality Gate PASS con limitaciones (REV-01 Medium, REV-02/03 Low abiertos) | delivery-publish |

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
**Resumen.** Módulo nuevo `backend/modules/receivables` (dominio `Obligation`, casos de uso `CollectionService`, repositorio con bloqueo de fila, API `/api/receivables/`), fachadas `services.py` en `quotations` y `dentistry` (con marca monótona `collected` y migraciones aditivas `quotations/0003`, `dentistry/0004`), DTO neutro `shared/domain/commitment.py`, registro en el catálogo de módulos y feature Angular `receivables` (lista, detalle con formulario de pago y resumen), botones «Cobrar» y enlace en la ficha del paciente, i18n es/en/pt.

**Cobertura.** INV-01..05, 09 y AC-04/07: `receivables/domain/obligation.py` + `tests/test_domain.py`. INV-06/07 y AC-02/03: `collections.py` (clave + hash, bloqueo obligación → proforma) + `tests/test_api.py`. INV-08/AC-06: `rectify` de ambos agregados + `CollectedLineTests`. AC-01/05/08/09/10: `tests/test_api.py`. AC-08/11: specs de componentes. AC-12: `i18n:check` y prueba de claves.

**Desviaciones respecto al plan.**
- `ALLOWED_DEPENDENCIES['receivables'] = {quotations, dentistry}` (sin `customers`): el nombre del cliente viaja en el snapshot de la fuente. `ModuleDefinition('receivables')` no `requires` nada (opcionales: quotations, dentistry).
- El formulario de pago es un panel dentro del detalle (no un modal); mismo contenido y pasos (DDR admite «panel/diálogo»).
- La marca `collected` también se propaga a copias en versiones posteriores ya creadas (borradores) para que no se pueda rectificar tras presentar.
- El filtro por fecha de la lista usa la fecha de alta de la obligación (primer pago). El filtro por estado se aplica en memoria (volumen de un consultorio); sin N+1 gracias a la lectura por lote.
- `collectible` en el detalle de proformas es opcional en los modelos del frontend para no romper fixtures.

**Deuda técnica.** Lista de Cobros paginada en memoria; pantalla sin impresión de comprobante; sin anulación de pagos ni profesional por línea (fuera de alcance).

**Pantallas.** Referencias: `quotations/pages/proforma-list` (lista), `proforma-detail` (detalle). Se reutilizan `MoneyPipe`, badges `col-*` y `Page`; no se crearon componentes compartidos.

**Verificación propia (no es el Quality Gate).** Backend: pruebas de dominio, límites de módulos, guards y catálogo (74) en verde con el Python del repo principal. Las pruebas de integración con PostgreSQL (`receivables/tests/test_api.py`, incluida la concurrencia) están escritas y compilan pero **no se pudieron ejecutar**: no hay credenciales de base de datos en este entorno. Frontend: `ng build`, `ng lint`, `i18n:check` y 1310 pruebas en verde; 1 fallo previo e independiente (`screens-i18n.spec.ts`, «Delivered»/«Entregado»), que también falla en `main`.

## Review
Resultado: **PASS con limitaciones**. Hallazgos abiertos (no bloqueantes):
- [REV-01](docs/reviews/REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-01.md) Medium — «hoy» del pago usa fecha UTC en backend y frontend en lugar de la zona horaria de la empresa.
- [REV-02](docs/reviews/REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-02.md) Low — tras un 409 el FormArray de imputaciones no se reconstruye (posible desalineación por índice).
- [REV-03](docs/reviews/REV-2026-11-04-cobrar-servicios-anticipos-pagos-parciales-03.md) Low — `except Exception: continue` en la lista de Cobros (bandit B112).
Consistencia visual: revisada solo por lectura; no verificada en navegador.

**Actualización 2026-11-05 — verificación con PostgreSQL y revisión manual** (a pedido del usuario, con la BD de pruebas por `TEST_DATABASE_NAME`):
- `manage.py test modules.receivables` → `Ran 22 tests ... OK` (incluye idempotencia, concurrencia con hilos, versionado, rectificación bloqueada, aislamiento por empresa, módulo deshabilitado y proforma odontológica).
- Suite completa del backend → `Ran 1499 tests`, 1 fallo: `modularity/tests/test_api.py` fijaba la lista de módulos sin `receivables`. Corregido (prueba actualizada) y `modules.modularity` → `Ran 92 tests ... OK`.
- Revisión manual en el navegador (backend + `npm start`, empresa y usuario de prueba creados en la BD local de desarrollo; migraciones `dentistry.0004`, `quotations.0003`, `receivables.0001` aplicadas): botón «Cobrar» en la proforma; caso de la tarjeta reproducido (aceptado 300 → anticipo 100, saldo 200, estado Parcial, comprobante CB-000001 → abono 50, saldo 150, CB-000002); la línea rechazada no es cobrable; la línea ya pagada deja de ofrecerse; validación «la suma debe ser igual al monto»; paso de resumen; lista de Cobros con estado Parcial. Móvil (390 px): sin scroll horizontal de página, tablas con scroll propio. **No verificado:** tema oscuro de la app y flujo odontológico en navegador (cubierto por prueba de integración).
- Observación menor (sin REV): el resumen muestra el monto tal como se tecleó («Bs 100»).

## Publicación
PR #61 listo para aprobación humana (no se mergea). Cambio sensible: base de datos (migraciones aditivas en `receivables`, `quotations`, `dentistry`) y acceso por módulo/fuente; respaldo: ADR de módulo y de pagos. Pendiente de la persona que aprueba: ejecutar las pruebas con PostgreSQL (`python manage.py test`) y la revisión visual en navegador, y decidir si se corrige REV-01 antes del merge.
