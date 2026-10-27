# PLAN-2026-10-27-configuracion-por-modulo-y-empresa (v1)

**Task:** TASK-configuracion-por-modulo-y-empresa · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-configuracion-por-modulo-y-empresa-pantallas-configuracion · ADR-configuracion-por-modulo-y-empresa-modelo-y-contrato

## Objective
Que el administrador defina, por módulo y para su empresa, los ajustes de negocio (hoy los de Ventas), con valor inicial documentado, validación, historial de cambios (incluida la activación de módulos) y pantallas «General» / «Historial de cambios» en Ventas, Compras, Inventario y Módulos.

## Context
Ver TASK. Decisiones del usuario (2026-10-27): ajustes de Ventas = canal de venta predeterminado, método de pago predeterminado y descuento máximo (% del subtotal); Compras e Inventario muestran la pantalla con pestañas y aviso «sin ajustes»; el historial incluye habilitar/deshabilitar módulos; los predeterminados solo sugieren en la UI y el descuento máximo se valida en la API.

# Specification

## Domain context
Contexto ligero **Modularity** (configuración de la empresa), ahora también dueño del catálogo de ajustes y su historial. Relación nueva y acotada: **Sales** lee su configuración por la fachada `modularity.services` (ADR punto 7-8). Sin relación con Catalog, Customers, Expenses ni Reporting.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Ajuste (setting) | Parámetro configurable de un módulo, con clave estable, tipo y valor inicial | Historia PB-CFG-001 |
| Valor inicial / predeterminado | Valor que rige mientras la empresa no guarde otro | Historia («valor predeterminado») |
| Valor actual | Valor guardado por la empresa, o el inicial si nunca lo cambió | Historia |
| Ámbito (scope) del historial | Módulo cuyos ajustes se registran, o `modules` para la activación general | ADR |
| Historial de cambios | Registro inmutable de quién cambió qué ajuste, cuándo, valor anterior y nuevo | Historia |
Inconsistencia declarada: la historia llama «predeterminado» al valor inicial; en este plan son el mismo concepto.

## Current behavior
- No existe configuración por módulo: las reglas de Ventas son constantes (`backend/modules/sales/domain/order.py:285-292`, descuento ≤ subtotal; `backend/modules/sales/domain/enums.py` canales y métodos).
- `modularity` solo guarda módulos habilitados (`backend/modules/modularity/infrastructure/django/models.py:16-28`) y no registra quién ni cuándo (`application/use_cases.py:36-61`).
- La navegación solo tiene «Configuración › Módulos» (`frontend/panel_admin/src/assets/data/routes.json:135-145`, `app.routes.ts:87-93`); Ventas, Compras e Inventario son enlaces simples.

## Expected behavior
- Cada empresa tiene valores propios de los ajustes del catálogo; sin valor guardado rige el inicial.
- Ventas › Configuración (`/sales/settings`) permite ver/editar los 3 ajustes y guardar con validación; Compras e Inventario muestran la pantalla con el aviso de que no hay ajustes; Módulos suma la pestaña «Historial de cambios».
- Cada cambio real de un ajuste, y cada habilitación/deshabilitación de módulo, queda en el historial con usuario, fecha/hora, ajuste, valor anterior y nuevo.
- Los predeterminados de canal y método precargan el formulario de pedido y el registro de pago; el descuento máximo hace que Ventas rechace descuentos nuevos que lo superen.

## Domain rules / invariants
- INV-01 (nueva): cada ajuste tiene tipo y valor inicial definidos en el catálogo; sin fila guardada rige el inicial.
- INV-02 (nueva): una configuración inválida no se guarda; guardar es todo o nada (400 por campo).
- INV-03 (nueva): el historial es append-only; solo se registran cambios reales; guarda snapshots de etiqueta y nombre de usuario.
- INV-04 (nueva): los ajustes son por `company_id`; nunca se leen ni escriben por datos del cliente (la empresa sale del usuario autenticado).
- INV-05 (nueva): `max_discount_percent` ∈ [0, 100], `Decimal` con ≤ 2 decimales; `default_sales_channel` y `default_payment_method` ∈ valores del enum de Ventas o vacío.
- INV-06 (nueva): cambiar un ajuste no modifica pedidos, pagos ni totales existentes; la regla de descuento máximo solo se evalúa al aplicar un descuento (`apply_discount`).
- INV-07 (existente, PB-MOD-001): las reglas de dependencia de módulos siguen igual; ahora además registran historial.
- INV-08 (nueva): no se almacenan ni exponen secretos ni credenciales (el catálogo no admite ese tipo).

## Acceptance criteria
- AC-01: Solo el administrador de una empresa activa lee o cambia ajustes e historial; otra empresa no ve ni modifica los de la primera (404/403 según el caso, nunca datos ajenos).
- AC-02: Cada ajuste del catálogo expone `value`, `default`, etiqueta y descripción; una empresa sin cambios muestra los valores iniciales documentados (canal vacío, método vacío, descuento máximo 100).
- AC-03: Un valor inválido (enum desconocido, porcentaje fuera de 0–100, más de 2 decimales, no numérico, clave desconocida) responde 400 con el error en el campo y no guarda ningún ajuste de la petición.
- AC-04: Al guardar un valor distinto se crea un registro de historial por ajuste con usuario, fecha/hora, ajuste, valor anterior y valor nuevo; guardar sin cambios no crea registros.
- AC-05: Habilitar/deshabilitar un módulo (cuando cambia el estado) crea un registro de historial en el ámbito `modules`; las operaciones idempotentes no.
- AC-06: Historial: filtro por fecha (desde/hasta, inclusive) y por ajuste, orden más reciente primero, paginado; no contiene secretos.
- AC-07: Con `max_discount_percent` = N, aplicar un descuento > subtotal × N/100 a un pedido es rechazado con error en `discount`; los pedidos con descuentos anteriores no cambian; con N = 100 el comportamiento es el actual.
- AC-08: Los predeterminados de canal y método guardados precargan el formulario de pedido nuevo y el registro de pago (sin imponerlos: el usuario puede cambiarlos); sin predeterminado, los campos quedan como hoy.
- AC-09: UI: Ventas, Compras e Inventario tienen «Configuración» con pestañas «General» e «Historial de cambios»; Módulos tiene «General» (lista actual) e «Historial»; Compras e Inventario no muestran opciones futuras (solo el aviso).
- AC-10: UI: Guardar cambios muestra éxito o errores junto a cada campo y conserva lo introducido ante un error; Cancelar cambios restablece el último valor guardado; salir con cambios sin guardar pide confirmación.
- AC-11: Ajustar la configuración de un módulo deshabilitado se rechaza (409) y su menú/ruta no está disponible.

## Edge cases / Error cases
- EDGE-01: Módulo desconocido o base (`access`, `catalog`) en la URL → 404.
- EDGE-02: PATCH con `settings` vacío o ausente → 400; valor igual al actual → 200 sin historial.
- EDGE-03: Dos administradores guardan a la vez el mismo ajuste → último gana; cada cambio genera su registro con su valor anterior real (lectura y escritura dentro de `transaction.atomic()` con bloqueo de la fila del ajuste).
- EDGE-04: `changed_by_name` queda guardado aunque el usuario se elimine o renombre.
- EDGE-05: Historial sin filtros ni datos → lista vacía con `count = 0`; `date_from > date_to` o fecha mal formada → 400.
- EDGE-06: Falla de lectura de configuración desde Ventas → se usan los valores iniciales (comportamiento previo) y se registra el error.
- EDGE-07: Error de red al guardar en el frontend → mensaje y datos conservados, botón habilitado para reintentar.
- EDGE-08: Valor de porcentaje enviado como número JSON (`float`) → se parsea desde su texto con `Decimal`, nunca por `float`.

## Authorization / permissions
`CompanyAdminPermission` (por defecto de DRF) en todas las vistas; empresa de `company_id_from(request)`; actor de `request.user` (id y nombre, snapshot). El frontend no es barrera.

## API contract
Ver ADR punto 5.
- API-01: `GET /api/settings/<module>/` → 200 ajustes del módulo; 404.
- API-02: `PATCH /api/settings/<module>/` `{settings:{key:valor}}` → 200 / 400 por campo / 404 / 409 módulo deshabilitado.
- API-03: `GET /api/settings/<scope>/history/` con `date_from`, `date_to`, `setting`, `page` → 200 `{count, results, settings}` / 400 / 404.
- API-04: `GET/POST /api/modules/...` sin cambio de forma; internamente registran historial.
- Compatibilidad: endpoints nuevos; `POST /orders/<id>/discount` (o equivalente) puede responder un 400 nuevo por `discount` si supera el máximo configurado (comportamiento sin cambio con el valor inicial 100).

## UI behavior
- UI-01: Submenús Ventas (Pedidos, Configuración), Compras (Inicio, Configuración) e Inventario (Inicio, Configuración), filtrados por módulo habilitado (DDR, design-system §6).
- UI-02: `ModuleSettingsComponent` con pestañas General/Historial y filas de ajuste con etiqueta, descripción, valor, predeterminado, «Restablecer» y error junto al campo (DDR).
- UI-03: Compras/Inventario: aviso «sin ajustes configurables»; historial funcional.
- UI-04: `SettingsHistoryComponent` con filtros Desde/Hasta/Ajuste, tabla, paginación y estados cargando/vacío/error.
- UI-05: Aviso de cambios sin guardar (`canDeactivate` + `beforeunload`).
- UI-06: «Módulos» con pestañas General (lista existente) e Historial.

## Non-functional requirements
Textos en español; accesibilidad del design-system §7; dinero no aplica (el porcentaje es `Decimal`); sin dependencias nuevas; historial con índice `(company_id, scope, changed_at)`; paginación de 20.

## Out of scope
Ajustes P2 y contables P3; ajustes de Catálogo, Clientes, Gastos y Reportes; roles distintos de administrador; bloqueo 403 por módulo en la API de negocio (PB-MOD-004); exportar el historial; purga o edición del historial; funcionalidad de Compras e Inventario; aplicar en el backend los predeterminados de canal y método.

## Open questions
- PB-MOD-002 no está documentada en el repositorio; se asume que su alcance (menú y rutas por módulo habilitado) ya vino con PB-MOD-001 (`TASK-habilitar-modulos-por-empresa`). No bloquea.
- El descuento máximo no rige para descuentos ya existentes al editar ítems (`_check_amounts`): decisión de INV-06; si negocio quisiera lo contrario, es un cambio de Specification posterior.

# Test Specification

## Unit tests
- `modularity/tests/test_settings_domain.py`: catálogo coherente (claves únicas, módulos existentes y no base, valores iniciales válidos según su propia validación, choices = enums de Sales); validación de `choice` y `percent` (INV-05, EDGE-08); todo o nada.
- `sales/tests/test_domain.py`: `apply_discount` con `max_percent` (AC-07, INV-06).
- Frontend: `SettingsApiService`, `ModuleSettingsComponent` (valores, errores por campo, conservar datos, cancelar, deshabilitado sin cambios), `SettingsHistoryComponent` (estados, filtros), guard de salida, `SalesSettingsService`, menús (`sidebar-menu.spec.ts`).

## Integration tests
- `modularity/tests/test_settings_api.py`: GET inicial (AC-02), PATCH válido/ inválido/ parcial (AC-03, EDGE-02), historial creado y sin cambios (AC-04), aislamiento entre dos empresas (AC-01, INV-04), 403 sin empresa o empresa inactiva, 404 módulo base/desconocido (EDGE-01), 409 módulo deshabilitado (AC-11), historial: filtros, orden, paginación, 400 (AC-06, EDGE-05), snapshot de usuario (EDGE-04), concurrencia (EDGE-03).
- `modularity/tests/test_api.py` (existente): enable/disable generan historial `modules` y la idempotencia no (AC-05).
- `sales/tests/test_api.py`: descuento sobre el máximo configurado (AC-07), otra empresa con otro máximo, fallo de lectura → valores iniciales (EDGE-06).
- `sales/tests/test_boundaries.py` y `accounts/test_guards.py`: frontera `sales → modularity.services` y filtro por `company_id` del nuevo repositorio.
- Migración: solo `CreateModel`, sin `RunPython`.

## E2E
NO — flujo cubierto con integración y pruebas de componentes; no se instala Playwright. Verificación manual en publish: editar la configuración de Ventas con dos empresas, ver el historial, y salir con cambios sin guardar.

## Regression tests
`python manage.py test` completo, `npm test` (acotado a lo tocado más la comparación con la línea base de fallos preexistentes), `npm run lint`, `npm run build`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | test_settings_api aislamiento + 403; `test_guards` |
| AC-02 | test_settings_api GET inicial; test_settings_domain valores iniciales |
| AC-03 | test_settings_domain + test_settings_api 400 sin persistir |
| AC-04 | test_settings_api historial (con y sin cambios) |
| AC-05 | test_api (modularity) enable/disable → historial; idempotencia |
| AC-06 | test_settings_api filtros/orden/paginación; spec del componente de historial |
| AC-07 | sales test_domain + test_api; test de frontera |
| AC-08 | spec de `SalesSettingsService` y de `order-form`/`order-payments` (precarga) |
| AC-09 | spec de `ModuleSettingsComponent` (pestañas, aviso Compras/Inventario); `sidebar-menu.spec.ts`; spec de `ModuleListComponent` (pestañas) |
| AC-10 | spec de `ModuleSettingsComponent` y del guard de salida; verificación manual |
| AC-11 | test_settings_api 409; spec del `moduleGuard` existente |

# Implementation Plan

## Architecture considerations
ADR: ajustes en `modularity` con catálogo en código, «sin fila = valor inicial», historial append-only con snapshots, fachada de lectura para Sales, UI con componente parametrizado por módulo.

## Proposed solution
Dominio puro (`SettingDefinition`, `SETTINGS_CATALOG`, `validate`) + casos de uso (`GetSettings`, `UpdateSettings`, `ListSettingHistory`; `EnableModule`/`DisableModule` reciben el actor) sobre `DjangoCompanySettingRepository(company_id)` y `DjangoSettingChangeRepository(company_id)`; vistas DRF finas; fachada `modularity/services.py` consumida por el adaptador de Sales; en Angular `features/settings/` (componentes y servicio) y `SalesSettingsService` en `features/sales/`.

## Files/components affected
- Backend: `modularity/domain/settings.py`; `modularity/application/{use_cases,settings_use_cases}.py`; `modularity/infrastructure/django/{models,repositories}.py`; `modularity/api/{urls,views,serializers}.py`; `modularity/services.py`; `modularity/migrations/0002_*.py`; `modularity/tests/`; `sales/domain/order.py` (`apply_discount`), `sales/application/{ports,commands}.py`, `sales/infrastructure/adapters.py`, `sales/api/views.py` si hace falta; `sales/tests/test_boundaries.py`; `config/urls.py` solo si el prefijo `api/settings/` no cuelga del router de `modularity`.
- Frontend: `features/settings/{pages/module-settings,components/settings-history,services,models}`; cambios en `module-list` (pestañas); `features/sales/services/sales-settings.service.ts` y los componentes `order-form` y `order-payments`; `app.routes.ts` (`sales/settings`, `purchases/settings`, `inventory/settings`); `assets/data/routes.json`; `assets/i18n/{es,en,de}.json`; `sidebar-menu.spec.ts`; guard de salida en `core/guard/`.
- Docs: `docs/architecture/ddd.md` (nota de modularidad y mapa de dependencias), `docs/design/design-system.md` §5-§6, `docs/producto/modulos-implementados.md` (ajustes y valores iniciales).

## Implementation steps
1. Dominio: catálogo de ajustes y validación + pruebas (INV-01, INV-02, INV-05, EDGE-08).
2. Modelos y migración `0002` (solo `CreateModel`); repositorios con `company_id`; guard de fuga (AC-01, INV-03, INV-04).
3. Casos de uso y API de ajustes e historial (API-01..03, AC-02, AC-03, AC-04, AC-06, EDGE-01..05, AC-11).
4. Historial de módulos: actor en `EnableModule`/`DisableModule` y vista (AC-05, INV-07).
5. Fachada `modularity/services.py`, puerto/adaptador y regla `apply_discount(max_percent)` en Ventas; ajustar `test_boundaries.py` (AC-07, INV-06, EDGE-06).
6. Frontend: modelos, `SettingsApiService`, `ModuleSettingsComponent`, `SettingsHistoryComponent`, guard de salida, rutas y menú (UI-01..05, AC-09, AC-10, EDGE-07).
7. Pestañas en «Módulos» (UI-06) y precarga de predeterminados en pedido/pago (AC-08).
8. Documentación y suites completas.

## Database / migrations
Una migración nueva `modularity/0002_*` con dos `CreateModel`, la unicidad `(company_id, setting_key)` y los índices; sin `RunPython`. No se edita ninguna migración existente.

## Risks
- Nuevo acoplamiento `sales → modularity` (acotado y vigilado por test).
- Una lectura de configuración por cada «aplicar descuento»: una consulta indexada por llamada, aceptable.
- Ocultar menús no protege la API de módulos deshabilitados (PB-MOD-004, fuera de alcance); los ajustes sí exigen módulo habilitado (409).
- Concurrencia en guardados simultáneos (EDGE-03) → bloqueo de fila y test.
- Cambiar un valor inicial en código afecta a empresas que nunca guardaron el ajuste (documentado).

## New dependencies
Ninguna (`ngbNav` y `ngb-pagination` ya vienen con ng-bootstrap).
