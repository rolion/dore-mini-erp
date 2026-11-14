# TASK-libro-entradas-filtros-totales: Libro de entradas con filtros, totales y origen (PB-ACC-002)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-libro-entradas-filtros-totales
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/68
**Fuente:** https://trello.com/c/Tgy6EJhx/19-pb-acc-002-crear-libro-de-entradas-con-filtros-totales-y-origen

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-14 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (5194ccb, incluye PB-ACC-001) | delivery-start |
| 2026-11-14 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (nueva tabla con restricción única y contrato transaccional entre módulos, migración, contrato API, pantalla nueva) | delivery-start |
| 2026-11-14 | PLANNING → ENGINEERING | Specification READY: las ambigüedades se resolvieron con criterio propio y quedan registradas en el plan | delivery-start |
| 2026-11-14 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-11-14 | REVIEW → PUBLISH | Quality Gate PASS con reservas (3 hallazgos Low abiertos; revisión visual no verificada); a la espera de aprobación humana | delivery-publish |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-ACC-002 (P1, orden 2; **no es una Specification aprobada**). Historia: como administrador, consultar el dinero efectivamente cobrado desde productos y servicios en un libro común. Esperado:
- **Contrato de registro de entradas** en `accounting`. Campos: empresa, cuenta destino, moneda, monto positivo decimal, fecha efectiva del pago, fecha de creación, método, usuario y referencia estable al pago de origen (tipo productos/servicios + ID); datos para trazabilidad histórica y comprobante de origen cuando exista (CB-NNNNNN en servicios).
- Única por empresa/tipo de origen/ID de pago, también con concurrencia; reintento con datos incompatibles → conflicto; usable dentro de la misma transacción del pago; sin alta, edición ni borrado manual.
- **Menú Contabilidad → Entradas**: listado paginado, detalle, filtros por fecha efectiva, cuenta, método y origen; enlaces al pedido o comprobante según permisos; totales sobre **todos** los registros filtrados, monedas separadas sin conversión; periodo y cobertura histórica visibles; sin datos clínicos.
- Es un libro de cobros recibidos: no es devengamiento, utilidad ni saldo de cuenta; no cambia reporting ni suma servicios a ventas − gastos. Sin partida doble, fiscal, egresos, transferencias, saldos iniciales ni reversiones.
- Criterios: registro válido y rechazo de monto no positivo, referencias ajenas e incompatibilidad de moneda; concurrencia = una sola entrada y orígenes distintos con mismo ID no colisionan; totales y filtros coinciden con el conjunto completo; la cuenta original permanece tras cambiar el mapeo; sin acceso no se consulta detalle ni origen ajeno; sin endpoints de edición/borrado.
- Dependencia: PB-ACC-001 (hecha, PR #67). Tarjetas vecinas (fuera de este alcance): PB-ACC-003 (integra Ventas), PB-COB-002 (integra servicios), PB-ACC-004 (regularización histórica), PB-ACC-005 (validación final), PB-ACC-006 (reversiones).

### Hechos encontrados
- `accounting` ya existe con dominio/aplicación/infraestructura/api: `backend/modules/accounting/domain/account.py:39-101` (`Account`, `MethodMapping`, `can_receive`), `domain/catalog.py:5-14` (métodos `CASH, QR, BANK_TRANSFER, CARD, OTHER`, `FLOW_CURRENCY='BOB'`, `CURRENCIES=('BOB','USD')`), `infrastructure/django/models.py:7-39` (`AccountModel`, `MethodMappingModel`, `company_id` UUID sin FK), `api/urls.py:12-19` (solo cuentas y métodos).
- Fachada pública: `backend/modules/accounting/services.py:19-30` `resolve_account(company_id, method) -> AccountRef | None` (DTO inmutable; el comentario ya dice que quien registre la entrada guarda esa cuenta y no la recalcula).
- Las vistas de configuración de `accounting` no exigen el módulo habilitado (ADR de PB-ACC-001); las de negocio de otros módulos declaran `required_modules` (`backend/modules/receivables/api/views.py:110,132,141`). `shared/module_gate.py:23-34` ofrece `enabled_keys`/`is_enabled(company_id, key)` para saber si un módulo de origen está habilitado.
- Permiso por defecto de la API: `CompanyAdminPermission` (admin de empresa activa) — `backend/modules/accounts/api/permissions.py:11-23`. No existe otro rol de negocio hoy.
- **Pago de productos** (`sales`): `PaymentModel` sin `company_id` propio (hereda del pedido), sin usuario ni clave de idempotencia — `backend/modules/sales/infrastructure/django/models.py:59-73`; el pedido se identifica por UUID. Ruta de frontend: `sales/orders` (`app.routes.ts:143`).
- **Pago de servicios** (`receivables`): `PaymentModel` con `company_id`, `receipt_number` `CB-NNNNNN`, usuario y nombre, `payment_date`, `payment_method`, `idempotency_key` — `backend/modules/receivables/infrastructure/django/models.py:29-54`; el consecutivo se genera en `repositories.py:56-62`; la obligación se identifica por `source_kind` + `source_number` (número de proforma) y la pantalla es `receivables/:kind/:number` (`app.routes.ts:92`). `register_payment` exige transacción del llamante (`receivables/application/collections.py:68-69`).
- Ambos orígenes usan UUID para el id del pago, por lo que `(company_id, origin_kind, origin_id)` es una clave natural estable.
- Paginación DRF global `PageNumberPagination` tamaño 50 (`config/settings/base.py:103-104`); referencias de paginación propia con `page_size_query_param` en `agenda/appointments_api.py:21-24`.
- Frontend: plantilla «Lista de solo lectura con filtros» (`docs/design/design-system.md`, referencia `features/inventory/pages/movement-list`, con filtros, `ngx-datatable` paginado por servidor y enlace al documento solo si el servidor declara `source.available`). Menú estático `assets/data/routes.json:305-330` (Contabilidad con `adminOnly` y `module: accounting`); ruta actual `accounting/settings` en `app.routes.ts:105`.
- Fronteras: los módulos de negocio no importan infraestructura de otros; solo `services.py` (`docs/architecture/ddd.md:844-846`). Test de fronteras de referencia: `sales/tests/test_boundaries.py`.

### Hipótesis / supuestos no confirmados (resueltos en el plan)
- «Productos/servicios» = orígenes `PRODUCT` (pago de pedido de `sales`) y `SERVICE` (pago de `receivables`).
- Esta tarjeta **no** conecta Ventas ni Cobros: entrega el contrato (`services.record_entry`), la tabla y la consulta; las integraciones son PB-ACC-003 y PB-COB-002. El libro puede estar vacío hasta entonces.
- «Según permisos»: hoy solo el admin accede; el enlace al origen se muestra si el módulo propietario está habilitado para la empresa (mismo criterio que movimientos de inventario).
- «Cobertura histórica»: periodo realmente cubierto por el libro (primera y última fecha efectiva, y desde cuándo se registran entradas) con aviso de que los pagos anteriores no están hasta la regularización (PB-ACC-004).
- La entrada no copia texto libre del pago (referencia/notas) para no filtrar datos clínicos; se conserva el identificador del documento y el comprobante.

### Módulos y dependencias relacionadas
`accounting` (ampliado); `sales` y `receivables` solo como valores de origen y para saber si están habilitados (sin importarlos); `modularity` (gate); frontend `features/accounting`, `sidebar`/`routes.json`, i18n.

### Implementaciones similares existentes
Backend: libro de movimientos de inventario con idempotencia por origen (`ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo`) y pagos de Cobros con clave y hash de contenido. Frontend: `features/inventory/pages/movement-list`.

### Comportamiento actual
No existe ninguna entrada ni listado; los pagos solo viven en pedidos y Cobros.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id` desde el usuario, migración nueva (no editar `0001`), i18n es/en/pt, DDD pragmático, `services.py` como única entrada entre módulos, sin dependencias nuevas.

### Riesgos identificados
- Un `IntegrityError` dentro de la transacción del pago la dejaría inservible: el registro debe usar un punto de guardado y resolver la carrera sin romper la transacción externa.
- Totales sobre todo el conjunto: deben calcularse con agregación SQL, no sumando la página (riesgo de total parcial).
- Montos: `Decimal` de extremo a extremo; el JSON los entrega como texto.
- Fuga de datos entre empresas si algún filtro (cuenta, detalle) no se acota por `company_id`.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — tabla nueva con restricción de unicidad y contrato transaccional que consumirán dos módulos, migración, contrato API y pantalla nueva.

### Diseño requerido
**SI** — pantalla nueva (lista con filtros y totales, y detalle) y entrada de menú.

## Diseño
`docs/design/DDR-libro-entradas-filtros-totales-pantallas-entradas.md`

## Arquitectura
`docs/adr/ADR-libro-entradas-filtros-totales-registro-unico-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-11-14-libro-entradas-filtros-totales.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend** (`backend/modules/accounting/`): dominio `Entry` inmutable y `EntryValidationError/EntryConflict/EntryContractError` (`domain/entry.py`, INV-01, 02, 05), orígenes en `domain/catalog.py`; `EntryModel` y migración `0002_entry` (solo `CreateModel`; único `(company_id, origin_kind, origin_id)`, `CHECK amount > 0`, índices; INV-04); `DjangoEntryRepository` (inserción con punto de guardado, consulta filtrada, totales por moneda y origen con agregación SQL, cobertura); fachada `services.record_entry` + DTO `EntryInput`/`RecordedEntry` (exige transacción abierta, bloquea la cuenta, idempotente y con conflicto; AC-01..04, INV-03, 06); guarda en `UpdateAccount`: una cuenta con entradas no cambia de moneda (INV-08); API de solo lectura `GET /api/accounting/entries/` (paginada 20, totales/periodo/cobertura) y `/entries/<id>/` con `required_modules=('accounting',)` (API-01, 02; AC-05..09).
**Frontend** (`features/accounting/`): `models/entry.ts`, `EntriesApiService`, páginas `EntryListComponent` (filtros en la URL, totales por moneda, periodo y cobertura, estados cargando/vacío/vacío con filtros/error) y `EntryDetailComponent`; rutas con `moduleGuard('accounting')`, ítem de menú Entradas, claves i18n es/en/pt (UI-01..05). Referencia visual: «Lista de solo lectura con filtros» (`movement-list`/`purchase-list`) y Detalle (`product-detail`); no se creó ningún componente compartido (el bloque de totales vive en la página y se documenta como variante en design-system §5/§6).
**Cobertura:** AC-01, 03, 04, 06 → `test_entry_service.py`; AC-01/INV-01, 02, 05 → `test_entry_domain.py`; AC-02 → `test_entry_concurrency.py` (hilos); AC-05, 07, 08, 09 y INV-08 → `test_entries_api.py`; fronteras → `sales/tests/test_boundaries.py` (accounting sin dependencias); AC-10/UI → specs de `entry-list`, `entry-detail`, servicio y modelo, y `sidebar-menu.spec.ts`.
**Desviaciones respecto al plan (con motivo):**
1. No se añadieron rutas de `accounting` a `modularity/tests/test_enforcement.py`: el gate del libro se verifica en `test_entries_api.py::test_accounting_disabled_blocks_the_book` (403 `module_disabled`); esa lista cubre rutas de módulos con ciclo de enable/disable propio y las vistas de configuración de `accounting` tampoco están en ella.
2. Convención de `origin_document_ref` (sin cambio de esquema): para `PRODUCT` es el ID del pedido; para `SERVICE` es `<kind>/<number>` del compromiso de Cobros (p. ej. `quotation/PRO-0001`, `dental/…`), de modo que el enlace `receivables/:kind/:number` se arma sin importar `receivables`. Las integraciones (PB-ACC-003, PB-COB-002) deben respetarla.
3. `MoneyPipe` solo formatea bolivianos («Bs»): los importes del libro usan `formatAmount(amount, currency)` (BOB con el mismo texto de `money`; otras monedas como «70.00 USD»).
4. La API devuelve `source.id` (ID del pago de origen) solo en el detalle; el listado no lo expone.
5. `sidebar-menu.spec.ts` se actualizó (39 → 40 títulos; submenú de Contabilidad con Entradas).
**Deuda técnica / limitaciones:** el libro queda vacío hasta que PB-ACC-003/COB-002 llamen a `record_entry`; las etiquetas de método vienen del servidor en español (mismo patrón que la pestaña de métodos de PB-ACC-001). `screens-i18n.spec.ts` sigue siendo intermitente por orden aleatorio (ajeno, ya documentado en PB-ACC-001).
**Verificación propia (no es el Quality Gate):** backend suite completa 1569 tests OK (con `.env` copiado a este worktree con autorización del usuario, sin leerlo; ignorado por git) y `makemigrations --check` sin cambios; frontend `ng lint` OK, `npm run i18n:check` 1903 claves usadas / 0 faltantes, `ng build` OK, Karma acotado (`features/accounting` + `layout/sidebar`) 49/49 OK. No se ejecutó la suite completa de Karma ni inspección visual en navegador.

## Review
**Veredicto: PASS con reservas** (2026-11-14, subagente aislado; sin hallazgos Critical/High).
- Backend: suite completa 1569 tests OK; `makemigrations --check` sin cambios; bandit sobre `accounting` sin hallazgos. ruff y mypy no instalados: no ejecutados.
- Frontend: `npm run lint` OK; `i18n:check` 1903 claves, 0 faltantes; `ng build` OK; `npm audit --omit=dev` 0 vulnerabilidades. Suite completa de Karma: 1 ejecución 1386 OK y 4 con 1 fallo en `screens-i18n.spec.ts` («labels coming from code follow the active language»), intermitente y preexistente (también falla en `main` por el orden aleatorio; el diff no la toca).
- Límites DDD, alcance del diff (sin tocar reporting, sales ni receivables), `record_entry` (transacción exigida, bloqueo de cuenta, punto de guardado, conflicto), totales en SQL, aislamiento por empresa, ausencia de escritura (405) y migración aditiva: conformes. Las 5 desviaciones declaradas están justificadas.
- Revisión visual en navegador: **no verificada** (solo lectura del código contra la checklist de design-system §8).
- Hallazgos Low (ahora resueltos, ver corrección posterior): [REV-01](../reviews/REV-2026-11-14-libro-entradas-filtros-totales-01.md) (EDGE-02: `account_id` bien formado pero inexistente da 200 vacío, sin fuga), [REV-02](../reviews/REV-2026-11-14-libro-entradas-filtros-totales-02.md) (API-03: `RecordedEntry` es un DTO plano, no `{entry, created}`; desviación no declarada), [REV-03](../reviews/REV-2026-11-14-libro-entradas-filtros-totales-03.md) (sin test directo de EDGE-03/EDGE-06; «no admin» y «sin texto libre» probados de forma débil).
- **Corrección posterior (2026-11-14):** REV-01, REV-02 y REV-03 resueltos (cuenta desconocida en el filtro → 400; `RecordedEntry{entry, created}` según API-03; tests de EDGE-03, EDGE-06, no admin y claves exactas del listado). Verificado: backend 1571 tests OK. Frontend sin cambios. Sigue pendiente la revisión visual en navegador.

## Publicación
PR #68 listo para aprobación humana; no se mergea. Cambios sensibles: **base de datos** (migración `accounting/0002_entry`, solo `CreateModel`, con restricción única y `CHECK`) y **arquitectura** (contrato transaccional entre módulos, ADR-libro-entradas-filtros-totales-registro-unico-y-contrato). No hay cambios de autenticación ni de infraestructura.
