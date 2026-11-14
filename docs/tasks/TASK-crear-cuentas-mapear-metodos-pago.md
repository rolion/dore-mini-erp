# TASK-crear-cuentas-mapear-metodos-pago: Crear cuentas y mapear métodos de pago por empresa (PB-ACC-001)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-crear-cuentas-mapear-metodos-pago
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/67
**Fuente:** https://trello.com/c/38XLSMLH/18-pb-acc-001-crear-cuentas-y-mapear-m%C3%A9todos-de-pago-por-empresa

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-13 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello; `main` al día (785c2bd) | delivery-start |
| 2026-11-13 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (módulo nuevo, habilitación con precondición, contrato API, migración) | delivery-start |
| 2026-11-13 | PLANNING → ENGINEERING | Specification READY: las decisiones abiertas se resolvieron con criterio propio y quedan registradas en el plan | delivery-start |
| 2026-11-13 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-11-13 | REVIEW → PUBLISH | Quality Gate PASS (3 hallazgos Medium y 5 Low abiertos); a la espera de aprobación humana | delivery-publish |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-ACC-001 (P1, orden 1; **no es una Specification aprobada**). Historia: como administrador, configurar dónde se recibe el dinero antes de habilitar el libro de entradas. Esperado: base del módulo `accounting` y su habilitación por empresa (perfiles de productos y de odontología); **cuentas destino** con nombre, moneda y estado activo/inactivo; **configuración método → cuenta** por empresa (varios métodos pueden usar una cuenta; cada método tiene un único destino vigente). Menú: Contabilidad → Configuración → Cuentas y Métodos de pago. Crear, editar, desactivar (las cuentas con historial no se eliminan). Rechazar referencias ajenas e incompatibilidad de moneda. Desactivar una cuenta usada por métodos activos exige reasignar o desactivar esos métodos. La cuenta se resuelve en servidor al cobrar; cambiar el mapeo solo afecta pagos posteriores. No crear cuentas ficticias ni mapear históricos. Habilitar accounting exige mapeo completo de los métodos activos de los flujos de cobro habilitados; con accounting deshabilitado se conserva el comportamiento actual. Fuera de alcance: partida doble, fiscal, egresos, transferencias, saldos iniciales, reversiones; no tocar el reporte ventas − gastos. Criterios: Empresa A (Efectivo→Caja, Transferencia/QR→Banco) y B con destinos propios; rechazar cuenta ajena, moneda incompatible y desactivación que deje métodos sin destino; cambiar Transferencia de Banco A a B conserva la cuenta de movimientos previos; permisos admin y estados de carga/vacío/error/éxito; habilitar exige configuración completa.

### Hechos encontrados
- Los dos flujos de cobro usan los **mismos códigos** `CASH, QR, BANK_TRANSFER, CARD, OTHER`, pero cada módulo tiene su propio enum: `backend/modules/sales/domain/enums.py:35-40` y `backend/modules/receivables/domain/obligation.py:19-25` («Mismos métodos que Ventas; todos se consideran activos»). Compras y Gastos tienen enums idénticos propios (`purchases/domain/enums.py:34`, `expenses/domain/enums.py:11`) pero son egresos: fuera de alcance. No existe un catálogo compartido ni un concepto de «método inactivo».
- El pago se guarda como texto `payment_method` en `sales/infrastructure/django/models.py:63` y `receivables/infrastructure/django/models.py:33`; Ventas lo registra en `Order.register_payment` (`sales/domain/order.py:348`), Cobros en `Obligation.register_payment` (`receivables/domain/obligation.py:145`). Ninguno guarda cuenta.
- Moneda: los flujos son fijos en `BOB` (`quotations/domain/proforma.py:7`, `receivables/api/serializers.py:6`); no hay multimoneda.
- Catálogo de módulos en código: `modularity/domain/modules.py:16-33` (`MODULE_CATALOG`, `DEFAULT_ENABLED_KEYS` en `:39`); no existe `accounting`. `EnableModule` (`modularity/application/use_cases.py:51`) solo valida dependencias obligatorias. Habilitados por defecto: customers, sales, expenses, reporting; `accounting` no será de ellos (comportamiento actual intacto).
- Gate por módulo: las vistas declaran `required_modules` (p. ej. `receivables/api/views.py:110`); el puerto lo resuelve `modularity/infrastructure/django/gate.py`. `test_enforcement.py` lista cada ruta de negocio con su módulo.
- Aislamiento: `backend/shared/tenancy.py`, repositorios con `company_id` en el constructor, `company_id` UUID indexado sin FK entre módulos (`docs/architecture/ddd.md:844`). Permiso por defecto `CompanyAdminPermission` (admin de empresa activa).
- Dependencias entre módulos permitidas solo vía `services.py`; un test de fronteras por módulo (`sales/tests/test_boundaries.py`) y `modularity` tratado como no-negocio (`ddd.md:846`).
- Frontend: menú estático `assets/data/routes.json` con campo `module` (ej. `:433`); rutas con `data: { module }` (`app.routes.ts:86-94`); plantilla «Configuración con listados en pestañas y diálogo» (`features/inventory/pages/inventory-configuration`, `docs/design/design-system.md:141`) y diálogos de `features/inventory/components`.
- No existe el concepto «perfil» de empresa: «productos» ≈ Ventas, «odontología» ≈ Cotizaciones/Odontología + Cobros.

### Hipótesis / supuestos no confirmados (resueltos en el plan)
- «Perfiles» = combinaciones de módulos habilitados (Ventas y/o Cobros); no se crea un modelo de perfil.
- Los flujos de cobro habilitados son Ventas (`sales`) y Cobros (`receivables`).
- Todos los métodos del catálogo están activos por defecto; el admin puede desactivar uno (p. ej. «Otro»).
- La única moneda de los flujos es BOB; las cuentas pueden crearse en otra moneda pero no se pueden asignar a un método.

### Módulos y dependencias relacionadas
Nuevo `accounting`; `modularity` (catálogo, habilitación con precondición y gate); Ventas y Cobros solo como claves de flujo, sin cambios en sus APIs ni dominios en esta entrega; frontend `layout/sidebar`, `app.routes.ts`, `features/accounting` nuevo.

### Implementaciones similares existentes
Backend: `service_catalog`/`inventory` (catálogos con activar/desactivar, repositorio con `company_id`). Frontend: `features/inventory/pages/inventory-configuration`.

### Comportamiento actual
No hay cuentas ni cajas; pagos solo con texto de método.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id` desde el usuario, no editar migraciones aplicadas, i18n es/en/pt sin texto hardcodeado, DDD pragmático.

### Riesgos identificados
- Ciclo de dependencia `modularity` ↔ `accounting` (mitigado en el ADR con un puerto de precondición).
- Mapeo incompleto si más adelante se habilita un flujo de cobro con accounting activo (se valida en la habilitación; el bloqueo posterior queda para las historias de entradas).
- Divergencia entre los códigos de método de Ventas/Cobros y el catálogo de accounting (test de correspondencia).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — módulo nuevo, migración, contrato API, precondición en la habilitación de módulos y nueva dependencia entre módulos.

### Diseño requerido
**SI** — pantalla nueva de configuración con diálogos y entrada de menú.

## Diseño
`docs/design/DDR-crear-cuentas-mapear-metodos-pago-pantalla-cuentas-metodos.md`

## Arquitectura
`docs/adr/ADR-crear-cuentas-mapear-metodos-pago-modulo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-11-13-crear-cuentas-mapear-metodos-pago.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
**Backend** (`backend/modules/accounting/`): dominio puro (`catalog.py`, `account.py`: INV-01..05, 07, EDGE-05), modelos `AccountModel`/`MethodMappingModel` con migración `0001_initial` (solo `CreateModel`, único `(company_id, method)` y nombre sin distinguir mayúsculas), repositorios por empresa, casos de uso, API `/api/accounting/accounts|payment-methods/` (API-01..03) sin exigir el módulo habilitado, y fachada `services.py` (`resolve_account`, `missing_method_labels`). Clave `accounting` en el catálogo de `modularity`; `EnableModule` acepta un verificador de precondiciones y la API responde 409 `incomplete_configuration` con los métodos faltantes (INV-08, API-04). Registro en `INSTALLED_APPS` y `config/urls.py`.
**Frontend** (`features/accounting/`): `AccountingApiService`, página `AccountingSettingsComponent` con pestañas `AccountsTabComponent` (lista, filtro de estado, bloqueo 409) y `MethodsTabComponent` (5 filas, cuenta destino, estado, guardado por fila), `AccountDialogComponent`; ruta `accounting/settings` sin `moduleGuard`, ítem de menú Contabilidad, claves i18n es/en/pt (UI-01..04). Referencia: `inventory-configuration` (plantilla «listados en pestañas y diálogo»); se reutilizó el estilo de tabla apilada de `inventory/components/_inventory-table.scss`.
**Cobertura:** AC-01..06 → `accounting/tests/test_api.py`; AC-08 y reglas → `test_domain.py`; AC-05 con regresión de Ventas/Cobros → suite completa; AC-07/UI → specs de `features/accounting` y `sidebar-menu.spec.ts`.
**Desviaciones respecto al plan (con motivo):**
1. La precondición de habilitación usa el puerto neutro `shared/enable_preconditions.py` en lugar de un adaptador `modularity → accounting.services`: el test de fronteras prohíbe que `modularity` importe módulos de negocio, y el patrón `shared/stock_history.py` ya existe. El ADR se actualizó (decisiones 5 y 7); no hay dependencia nueva entre módulos.
2. `missing_methods` no recibe los flujos habilitados: Ventas y Cobros comparten catálogo, se validan todos los métodos activos.
3. Selector de cuenta con `select` nativo (`form-select`) en lugar de `ng-select` del DDR (5 filas; más simple y accesible).
4. Menú de dos niveles (Contabilidad › Cuentas y Métodos de pago) como el resto del menú; no existe un tercer nivel «Configuración». Registrado en design-system §6.
5. UI-05 (enlace desde Módulos a la pantalla) no se implementó como enlace: el 409 de habilitar ya muestra el detalle «Falta configurar antes de habilitar: …» con los métodos faltantes mediante `ModulesService`.
**Deuda técnica / limitaciones:** el bloqueo de cobros con método inactivo y el guardado de la cuenta en cada entrada quedan para las historias del libro de entradas. `screens-i18n.spec.ts` («labels coming from code follow the active language») es intermitente por orden aleatorio de pruebas (fallo ajeno a este cambio: se observó 2 de 3 corridas del subconjunto `core/i18n`).
**Verificación propia (no es el Quality Gate):** backend suite completa 1531 tests OK (con `.env` copiado con autorización del usuario); frontend `ng lint` OK, `npm run i18n:check` OK (0 faltantes), `ng build` OK, Karma acotado `features/accounting` + `layout/sidebar` 23/23 OK. No se ejecutó la suite completa de Karma ni inspección visual en navegador.

## Review
**Veredicto: PASS** (2026-11-13, subagente aislado; sin hallazgos Critical/High).
- Backend: suite completa 1531 tests OK; `makemigrations --check` sin cambios; bandit sobre `accounting` sin issues en código de producción (solo B106 por una contraseña de prueba en un test). ruff/flake8/mypy no instalados: no ejecutados.
- Frontend: Karma acotado (`features/accounting` + `layout/sidebar`) 23/23 OK; `npm run lint` OK; `npm run i18n:check` 1872 claves, 0 faltantes (es/en/pt con 2153 claves iguales); `ng build` OK (solo warnings SCSS preexistentes).
- Límites DDD: dominio sin Django, sin imports entre módulos de negocio ni de `accounts`, consultas por `company_id`, migración solo aditiva, test de fronteras OK.
- Preexistente ajeno: `screens-i18n.spec.ts` («labels coming from code follow the active language») falla de forma intermitente también en el checkout principal sin estos cambios.
- No verificado: revisión visual en navegador (móvil, escritorio, oscuro), suite completa de Karma, ruff/flake8/mypy.
- Hallazgos abiertos: Medium [01](../reviews/REV-2026-11-13-crear-cuentas-mapear-metodos-pago-01.md) (test del contrato del gate), [02](../reviews/REV-2026-11-13-crear-cuentas-mapear-metodos-pago-02.md) (concurrencia EDGE-06), [03](../reviews/REV-2026-11-13-crear-cuentas-mapear-metodos-pago-03.md) (confirmación de desactivación UI-02). Low [04](../reviews/REV-2026-11-13-crear-cuentas-mapear-metodos-pago-04.md) a [08](../reviews/REV-2026-11-13-crear-cuentas-mapear-metodos-pago-08.md).

## Publicación
PR #67 listo para aprobación humana; no se mergea. Cambios sensibles: **base de datos** (migración `accounting/0001_initial`, solo esquema) y **autorización/habilitación de módulos** (precondición en `EnableModule`, ADR-crear-cuentas-mapear-metodos-pago-modulo-y-contrato).
