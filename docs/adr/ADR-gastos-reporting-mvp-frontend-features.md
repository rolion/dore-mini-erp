# ADR-gastos-reporting-mvp-frontend-features: Features Angular de Expenses y Reporting, piezas compartidas y entrega por fases

**Estado:** Propuesto
**Task relacionado:** TASK-gastos-reporting-mvp
**Fecha:** 2026-10-09

## Contexto
`ddd.md:1067-1090` fija `features/expenses/{expense-list,expense-form}` y `features/dashboard/`. El código actual (en `main`) organiza cada módulo en `features/<modulo>/{pages,components,services,models,testing}` con `index.ts` y rutas `loadChildren` en `app.routes.ts`; los features no se importan entre sí (cada uno tiene su propio servicio de API, p. ej. `features/customers/services/customer-orders-api.service.ts` y `features/sales/services/customer-options.service.ts`). `MoneyPipe` y las etiquetas de canal viven en `features/sales` (`pipes/money.pipe.ts`; `SALES_CHANNELS`/`SALES_CHANNEL_LABELS` en `models/order.ts`) y los necesitarán Expenses y Reporting. `shared/` solo tiene `models/page.ts` y `styles/_table-actions.scss`. El dashboard actual es `dashboard/main` (plantilla con datos de ejemplo) enrutado en `dashboard/dashboard.routes.ts` como `main`. Un test fija el menú (`layout/sidebar/sidebar-menu.spec.ts`). El DDR de [pantallas de gastos](../design/DDR-gastos-reporting-mvp-menu-y-pantallas-gastos.md) y el de [dashboard y reportes](../design/DDR-gastos-reporting-mvp-dashboard-y-reportes.md) son la entrada. Regla del proyecto: **una rama y un PR por task**.

## Decisión

**Estructura:**
- `src/app/features/expenses/`: `pages/{expense-list,expense-form,expense-detail,category-list}`, `components/category-dialog` (alta/edición en `NgbModal`), `services/{expenses-api,categories-api}.service.ts`, `models/{expense,category}.ts`, `testing/*-fixtures.ts`, `expenses.routes.ts`, `index.ts`. Rutas bajo `/expenses` (lista, `new`, `:id`, `:id/edit`) y `/expenses/categories`, con `loadChildren` en `app.routes.ts`.
- `src/app/features/reporting/`: `pages/{dashboard,reports}`, `components/{period-selector,kpi-card,...}`, `services/reporting-api.service.ts`, `models/report.ts`, `testing/`, `reporting.routes.ts`. `/reports` carga `reports`; la ruta existente `dashboard/main` pasa a cargar `features/reporting` `DashboardPage` y **se eliminan** los archivos de ejemplo `dashboard/main/*` (se conserva `dashboard2` y su ruta, no relacionados). El path `/dashboard/main` y su entrada de menú no cambian.
- **Sin importaciones entre features.** El selector de periodo, las tarjetas y la tabla de ranking viven en `features/reporting` y los usan sus dos páginas; Reportes y Gastos no se importan.

**Piezas compartidas (se mueven a `shared/`, cambio mecánico en Sales):**
- `MoneyPipe` → `src/app/shared/pipes/money.pipe.ts`; `features/sales` actualiza sus imports (3 componentes + `order-detail`).
- `SalesChannel`, `SALES_CHANNELS` y `SALES_CHANNEL_LABELS` → `src/app/shared/models/sales-channel.ts`; `features/sales/models/order.ts` los re-exporta o importa desde ahí para no romper pruebas existentes.
- Los estilos de acciones de tabla ya están en `shared/styles/_table-actions.scss` y se reutilizan.
No se mueve nada más ni se crea una librería de componentes.

**Estado y tipos:** servicios inyectables sin lógica visual; tipos explícitos (sin `any`); Reactive Forms tipados; respuestas del servidor mapeadas a modelos (importes como `string`, fechas ISO como `string`); suscripciones con `takeUntilDestroyed`/`async` pipe. Cada tarjeta/informe del dashboard y de Reportes tiene su propio estado `loading | error | data` y botón "Reintentar" (rutas independientes del [ADR de contrato de reportes](ADR-gastos-reporting-mvp-contrato-api-reportes.md)). El selector de periodo no calcula fechas: envía `period` o `date_from/date_to` y muestra el `period` recibido.

**Menú y traducciones:** `routes.json` pasa a 6 entradas (Dashboard, Catálogo, Cliente, Pedidos, **Gastos ▸ Gastos / Categorías**, **Reportes**); claves nuevas en `assets/i18n/{en,es,de}.json` (`MENUITEMS.EXPENSES.*`, `MENUITEMS.REPORTS.TEXT`) y `sidebar-menu.spec.ts` actualizado (6 rutas, 9 títulos). El contenido de las pantallas queda en español.

**Gráfico de dona:** no está verificado contra la plantilla (`panel_admin_doc/apex.html` no menciona dona/pie). El plan debe validar `type: 'donut'` en `ng-apexcharts` antes de adoptarlo; si no es viable, se usa una barra horizontal con el mismo layout.

**Entrega por fases, en un solo task y PR (commits separados):** (0) traer `main` a la rama (Sales no existe aquí); (1) backend Expenses; (2) frontend Expenses + menú; (3) fachadas de Sales y Expenses, test de límites y backend Reporting; (4) frontend Reporting, retirada del dashboard de ejemplo y movimiento a `shared/`; (5) documentación (`ddd.md`). Cada fase deja las suites en verde. Si el plan estima que el PR es demasiado grande para revisarse, el corte natural es entre las fases 2 y 3 (Gastos primero, Reporting después), pero eso exigiría dividir el task en dos, decisión de `delivery-plan`/usuario, no de este ADR.

## Alternativas consideradas
- **Un solo `features/dashboard/` (como en `ddd.md:1084`) en lugar de `features/reporting/`:** el nombre `dashboard` ya existe como carpeta de la plantilla; el módulo de negocio se llama Reporting y alberga dos páginas (dashboard y reportes). Se elige `reporting` y se actualiza `ddd.md`.
- **Importar `MoneyPipe` y etiquetas desde `features/sales`:** evita mover archivos, pero crea acoplamiento entre features (hoy no hay ninguno) y haría que Expenses/Reporting dependan de Sales aunque su dominio no lo haga. Moverlos a `shared/` es un cambio mecánico y pequeño.
- **Duplicar el pipe y las etiquetas en cada feature:** rápido pero produce tres copias que divergen (formato "Bs").
- **Reescribir el dashboard conservando `dashboard/main` y su carpeta:** deja la plantilla con datos de ejemplo mezclada con código real; se prefiere que lo real viva en `features/reporting` y borrar el ejemplo.
- **Dividir en dos tasks desde ahora:** reduce el tamaño del PR, pero Reporting depende de Expenses y Sales; el costo de dos ciclos completos supera el beneficio mientras las fases mantengan commits revisables (Sales entregó 16 REQ + frontend en un task). Se deja como opción para el plan.

## Estrategia de rollback / mitigación
Aditivo en su mayoría: features y rutas nuevas. Los cambios sobre código existente son (a) retirar `dashboard/main` (se recupera revirtiendo el commit), (b) mover `MoneyPipe` y el modelo de canal (las pruebas de Sales deben seguir en verde), (c) `routes.json` y su spec. Rollback = revertir el PR; si solo falla Reporting, se puede quitar la ruta `/reports` y la entrada de menú sin tocar Gastos. Mitigación: el movimiento a `shared/` va en un commit propio con las pruebas de Sales ejecutadas antes y después.

## Consecuencias
- Queda fácil: ambas features siguen el molde de Clientes/Pedidos; el dashboard deja de tener datos ficticios; Pipe y etiquetas centralizados.
- Queda más difícil: el PR es grande; el movimiento a `shared/` toca archivos de Sales (riesgo bajo, mecánico).
- Deuda aceptada: contenido de pantallas solo en español; dona pendiente de validar; `catalog`/`customers` siguen sin usar el `MoneyPipe` compartido (no lo necesitan hoy).
