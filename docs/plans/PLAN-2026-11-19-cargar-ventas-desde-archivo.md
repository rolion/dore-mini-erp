# PLAN-2026-11-19-cargar-ventas-desde-archivo (v1)

**Task:** TASK-cargar-ventas-desde-archivo · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `DDR-cargar-ventas-desde-archivo-asistente-de-importacion`, `ADR-cargar-ventas-desde-archivo-modulo-e-integracion-por-fachadas`, `ADR-cargar-ventas-desde-archivo-ejecucion-por-venta-e-idempotencia`

## Objective
Permitir que el administrador suba un CSV/Excel de ventas, lo mapee a los campos del sistema, elija qué se infiere (productos, clientes, inventario/compras, movimientos contables), previsualice y cargue: cada venta queda entregada y cobrada con sus movimientos de inventario, costo y contabilidad, creando lo que falte.

## Context
Ver `docs/tasks/TASK-cargar-ventas-desde-archivo.md` (investigación, decisiones del usuario y riesgos).

# Specification

## Domain context
Nuevo contexto **Importación de datos** (`data_import`) que orquesta Sales, Catalog, Customers, Purchases, Inventory, Costing y Accounting solo por sus fachadas `services.py`. Reporting no cambia.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Importación (`ImportRun`) | Un archivo subido con su mapeo, opciones y resultado | nuevo |
| Venta importada | Grupo de filas con el mismo n.º de venta (o una fila) que genera un pedido | nuevo |
| Mapeo | Correspondencia columna del archivo → campo de destino | nuevo |
| Inferir | Crear automáticamente lo que no existe (producto, cliente, compra/proveedor, asientos) | requerimiento |
| Faltante | Cantidad vendida que excede el saldo del almacén en ese momento | nuevo |
| Cobertura contable | Fecha ≥ corte con Contabilidad habilitada (`coverage_status`) | `accounting/services.py:170` |
| Pedido / Cobro / Recepción / Compra | ya definidos | `sales`, `purchases` |

## Current behavior
Sin importación: ventas y compras solo manuales (`sales/application/commands.py:50-295`, `purchases/application/receipt_commands.py:56`). Ver TASK.

## Expected behavior
1. **Subir** `.csv` o `.xlsx` (≤ 5 MB, ≤ 2 000 filas de datos); el servidor lee cabeceras, cuenta filas, devuelve 5 filas de muestra, una sugerencia de mapeo y las capacidades de la empresa (módulos habilitados, almacenes, métodos de pago).
2. **Mapear** campos: Fecha de venta*, Producto*, Cantidad*, Precio unitario* (obligatorios); N.º de venta, Cliente, Método de pago, Canal, Proveedor, Costo unitario, Notas (opcionales); con las **cuatro casillas** de inferencia y valores por defecto (método de pago **CASH/Caja**, canal OTHER, almacén).
3. **Vista previa** sin escribir: contadores y problemas por fila.
4. **Cargar**: cada venta, en orden cronológico y en su propia transacción: (a) cliente, (b) productos, (c) con «inferir inventario», proveedor y compra recibida por el faltante, (d) pedido con el precio del archivo, entregado en la fecha de la venta con salida de stock y costo, (e) cobro por el total en la fecha de la venta con el método de la fila o el predeterminado, (f) asientos que cada módulo ya genera cuando hay cobertura y se marcó «movimientos contables».
5. **Resultado** por venta y historial; reintentar el mismo archivo no duplica.

## Domain rules / invariants
- **INV-01 (existente)** Aislamiento por empresa: todo se filtra por `company_id` del usuario (`shared/tenancy.py`); nunca del cliente.
- **INV-02 (existente)** Dinero en `Decimal` con 2 decimales; cantidad entera > 0 y ≤ 100 000 (`sales/domain/order.py:93`); precio ≥ 0.
- **INV-03 (existente)** Fechas: ni futuras ni vacías; entrega = cobro = fecha de la venta (`order.deliver`, `register_payment`).
- **INV-04 (nueva)** Unidad atómica = una venta: o se crean todos sus efectos (cliente, productos, proveedor, compra, pedido, cobro, asientos) o ninguno.
- **INV-05 (nueva)** Idempotencia por `source_key` único por empresa (`n:<n.º venta>` o `h:<hash>:<n>`): una venta ya importada nunca se vuelve a crear.
- **INV-06 (nueva)** El pedido importado conserva el **precio del archivo**; el catálogo existente no se modifica.
- **INV-07 (nueva)** Coincidencia de producto/cliente/proveedor por nombre normalizado (minúsculas, sin tildes, espacios colapsados); sin inferencia, lo inexistente es error de fila.
- **INV-08 (nueva)** Compra inferida = solo por el faltante, recibida en la fecha de la venta, al costo de la fila o costo promedio vigente; queda **sin pago**; sin costo con cobertura contable → error de fila.
- **INV-09 (nueva)** Una sola ejecución activa por empresa.
- **INV-10 (nueva)** Con «movimientos contables» desmarcado no se genera ningún asiento (ventas, costo, compras) aunque haya cobertura; la vista previa lo advierte.

## Acceptance criteria
- **AC-01** Subir CSV/XLSX válido devuelve id, cabeceras, 5 filas de muestra, `row_count`, mapeo sugerido y capacidades. Se rechazan: tipo distinto, > 5 MB, vacío, sin cabeceras, > 2 000 filas, `.xlsx` corrupto o con zip sospechoso (400 con mensaje).
- **AC-02** El mapeo sugerido reconoce cabeceras comunes (es/en/pt) sin distinguir tildes/mayúsculas; la persona puede cambiarlo.
- **AC-03** Con un campo obligatorio sin mapear o una columna inexistente, la vista previa responde 400 y la UI no avanza.
- **AC-04** Existen cuatro casillas; las que dependen de un módulo deshabilitado (Clientes; Inventario **y** Compras; Contabilidad) se rechazan en el servidor si se envían activas y se muestran deshabilitadas con motivo.
- **AC-05** Método de pago por fila (sinónimos: efectivo/caja→CASH, qr, transferencia, tarjeta, otro) o el predeterminado (por defecto CASH); canal por fila o predeterminado; almacén requerido solo si hay productos con stock controlado.
- **AC-06** La vista previa no escribe nada en ningún módulo y devuelve: ventas/líneas leídas, a cargar, ya importadas, con error, productos y clientes nuevos/existentes, compras a crear y unidades a comprar, ventas sin cobertura contable y hasta 200 problemas por fila con campo y mensaje.
- **AC-07** Cargar crea por cada venta válida un pedido `DELIVERED` y `PAID` en su fecha, con el precio del archivo, salidas de stock del almacén y, con las condiciones de AC-11, costo y asientos.
- **AC-08** Con «inferir productos» crea los inexistentes (activo, vendible, precio de la primera fila; stock controlado solo con Inventario habilitado e «inferir inventario»); sin la casilla, un producto inexistente deja la venta con error.
- **AC-09** Con «inferir clientes» crea los inexistentes por nombre; sin la casilla, un cliente inexistente es error; sin columna de cliente la venta queda sin cliente.
- **AC-10** Con «inferir inventario» y faltante > 0 crea el proveedor (de la fila o «Importación») y una compra recibida por el faltante (entradas de stock, costo, reconocimiento contable), sin pago; sin faltante no crea compra; sin costo (fila ni promedio) con cobertura → error de la venta.
- **AC-11** Con «movimientos contables» y cobertura: reconocimiento de la venta al entregar, costo de ventas, cobro contra Cuentas por cobrar y, en compras, Debe Inventario / Haber Cuentas por pagar, igual que los flujos manuales. Con la casilla desmarcada o Contabilidad deshabilitada no hay asientos.
- **AC-12** Venta con fecha sin cobertura: se carga sin asiento (cobro por el libro anterior como hoy), con estado «Cargada sin asiento» y aviso; si el método de pago no tiene cuenta destino, error accionable de la venta.
- **AC-13** Si una venta falla, no queda nada de ella (ni pedido, ni compra, ni productos/clientes creados en ella) y se informa fila, venta y motivo; las demás continúan.
- **AC-14** Volver a subir/ejecutar el mismo archivo (o uno corregido con los mismos n.º de venta) no crea duplicados: reporta «Ya importada»; ejecutar de nuevo una importación completada devuelve su resultado guardado.
- **AC-15** Ejecutar mientras otra importación de la empresa corre responde 409 `import_running`.
- **AC-16** Solo administradores con `sales` y `catalog` habilitados; una importación de otra empresa responde 404; el cliente no puede enviar `company_id`.
- **AC-17** Resultado y historial paginados: contadores por estado, mensajes por venta, enlace al pedido creado.
- **AC-18** Validaciones de campo: fecha futura/ inválida, cantidad no entera/≤0/> máximo, precio negativo/más de 2 decimales/no numérico, textos recortados a sus máximos y sin caracteres de control; cada error indica fila y campo.
- **AC-19** UI: cuatro pasos con estados cargando/vacío/error/éxito, móvil, foco y accesibilidad según DDR; todo el texto por `translate` con claves iguales en `es/en/pt`.
- **AC-20** `data_import` solo importa fachadas `services.py` de otros módulos (test de fronteras) y nadie importa `data_import`.

## Edge cases / Error cases
- Fila con n.º de venta repetido y fechas, cliente o método distintos: error «las líneas de una venta deben coincidir» (usa la de la primera si solo difiere la nota).
- Misma venta con el mismo producto en dos líneas: se aceptan (el pedido ya suma líneas repetidas al entregar).
- Producto controlado con política de stock negativo desactivada y sin «inferir inventario»: error de stock insuficiente de la venta (mensaje del módulo).
- Producto inactivo o no vendible: error de la venta; cliente inactivo: error.
- Archivo con BOM, delimitador `;`, decimales con coma (`12,50`) y fechas `dd/mm/aaaa`, `aaaa-mm-dd` o seriales de Excel: se normalizan; ambigüedad día/mes se resuelve con el formato elegido en el mapeo (por defecto `dd/mm/aaaa`).
- Filas totalmente vacías se ignoran; cabeceras duplicadas → 400.
- Dos importaciones simultáneas de la misma empresa: 409; del mismo archivo sin concurrencia: duplicadas.
- Ruptura a mitad de ejecución (proceso caído): `ImportRun` queda `RUNNING` y se marca `FAILED` al detectarlo con una marca de latido; reintentar es seguro por idempotencia.

## Authorization / permissions
Permiso por defecto (administrador de empresa activa) + `required_modules = ('sales','catalog')`. Cada casilla exige además su módulo en servidor. 401/403 estándar.

## API contract
- **API-01** `POST /api/imports/sales/` (multipart `file`) → 201 `{id, filename, row_count, headers[], sample_rows[], suggested_mapping{}, capabilities{customers, inventory, purchases, accounting, costing, warehouses[{id,name,is_default}], payment_methods[], sales_channels[]}}`.
- **API-02** `POST /api/imports/sales/{id}/preview/` body `{mapping{}, options{infer_products, infer_customers, infer_inventory, infer_accounting, default_payment_method, default_sales_channel, warehouse_id, date_format}}` → 200 resumen + `problems[]` (máx. 200, con `row, sale_key, field, code, message`) + `problems_total`. 400 con errores por campo.
- **API-03** `POST /api/imports/sales/{id}/execute/` mismo body + `idempotency_key` (UUID) → 200 resultado `{id, status, counts{created, skipped, failed, without_posting}, rows_url}`; 409 `import_running`; 409 `posting_configuration_missing` como en Ventas.
- **API-04** `GET /api/imports/sales/` (paginado), `GET /api/imports/sales/{id}/`, `GET /api/imports/sales/{id}/rows/?status=` (paginado; incluye `order_id` y mensaje).
- **API-05** `GET /api/imports/sales/template/` → CSV de ejemplo con cabeceras.
- Compatibilidad: solo endpoints nuevos; sin cambios en contratos existentes. Fachadas nuevas con parámetros opcionales que mantienen el comportamiento actual.

## UI behavior
- **UI-01** Asistente de 4 pasos en `/pocketbiz/sales/import` según DDR (variante «de operación con previsualización obligatoria» §5), con las cuatro casillas **arriba del mapeo**.
- **UI-02** Historial `/pocketbiz/sales/import/history` y detalle `/:id` (Lista de solo lectura).
- **UI-03** Confirmación irreversible en `NgbModal` estático; botón deshabilitado y clave de idempotencia reutilizada en reintentos.
- **UI-04** 409/400 mostrados con mensaje accionable sin perder mapeo ni opciones; `app-posting-issues-alert` para configuración contable faltante.

## Non-functional requirements
Carga síncrona con límite 5 MB/2 000 filas (objetivo < 60 s para 500 ventas); no se guardan archivos binarios, solo filas normalizadas; accesibilidad AA; logs sin datos personales.

## Out of scope
Descuentos por venta, pagos a proveedores de las compras inferidas, devoluciones/reembolsos, reversa masiva de una importación, exportación de resultados, importación de compras/gastos/clientes por separado, `.xls`/`.xlsm`, varias hojas, ejecución asíncrona/cola de trabajos, edición de las ventas ya cargadas.

## Open questions (no bloquean)
- **OQ-01** Las compras inferidas se dejan **por pagar** (supuesto declarado; el usuario puede vetarlo en la revisión del PR).
- **OQ-02** Unidad por defecto de productos nuevos con stock controlado (nombre/abreviatura): se resuelve en build reutilizando una unidad existente o creando «Unidad (u)».
- **OQ-03** Formato de fecha por defecto `dd/mm/aaaa` (selector en el mapeo).

# Test Specification

## Unit tests
- Dominio `data_import`: normalización de nombres, parseo de fechas/decimales/enteros, sinónimos de método y canal, agrupación de filas en ventas, cálculo de `source_key`, validación de mapeo (AC-02, AC-03, AC-18, INV-05, INV-07).
- Parsers CSV/XLSX: BOM, delimitadores, Latin-1, vacías, cabeceras duplicadas, límites, zip sospechoso (AC-01).
- Cálculo del faltante cronológico y costo de la compra inferida (INV-08, AC-10).

## Integration tests
- Fachadas nuevas por módulo (catalog, customers, purchases, sales) con BD de prueba: creación, coincidencia por nombre, precio del archivo, aislamiento por empresa (AC-07..AC-10, INV-01, INV-06).
- Flujo completo con Inventario/Compras/Costeo/Contabilidad habilitados y cobertura: pedido DELIVERED+PAID, entradas y salidas de stock, costo promedio, asientos de venta/costo/cobro/compra balanceados (AC-07, AC-10, AC-11).
- Fecha sin cobertura, Contabilidad deshabilitada y casilla desmarcada: sin asientos y estado correcto (AC-11, AC-12, INV-10).
- Rollback por venta con fallo a mitad (producto inferido + compra no quedan) y continuación con las demás (AC-13, INV-04).
- Idempotencia: reejecución, archivo corregido, carrera con `IntegrityError` (AC-14, INV-05); 409 `import_running` (AC-15, INV-09).
- API: permisos, módulos requeridos, 404 entre empresas, contratos API-01..05 (AC-04, AC-16, AC-17).
- Frontera: test de dependencias de `data_import` (AC-20).

## E2E
**NO** — la cadena API (subir→previsualizar→cargar) ya se cubre con pruebas de integración y las pruebas de componentes de la UI; no se justifica instalar Playwright. Verificación manual guiada con un CSV de ejemplo en `delivery-publish`.

## Regression tests
Se ejecutan las suites existentes de `sales`, `purchases`, `catalog`, `customers`, `inventory`, `costing`, `accounting` y `modularity` (las fachadas nuevas no deben cambiar su comportamiento); prueba i18n (claves iguales en tres idiomas) y `npm run i18n:check`.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01 | Unit parsers + integración API-01 |
| AC-02 | Unit mapeo sugerido + componente (paso 2) |
| AC-03 | Unit validación + integración API-02 400 + componente (botón deshabilitado) |
| AC-04 | Integración API-02/03 con módulos deshabilitados + componente (casillas deshabilitadas) |
| AC-05 | Unit sinónimos/valores por defecto + integración con y sin stock controlado |
| AC-06 | Integración «preview no escribe» (conteo de filas en todos los módulos antes/después) |
| AC-07 | Integración flujo completo |
| AC-08 | Integración fachada catalog + flujo con/sin casilla |
| AC-09 | Integración fachada customers + flujo con/sin casilla |
| AC-10 | Unit faltante + integración compras/stock/costo/asiento, sin pago |
| AC-11 | Integración asientos balanceados con/sin casilla y módulo deshabilitado |
| AC-12 | Integración fecha anterior al corte + método sin cuenta |
| AC-13 | Integración rollback por venta |
| AC-14 | Integración idempotencia |
| AC-15 | Integración 409 concurrente |
| AC-16 | Integración permisos y 404 entre empresas |
| AC-17 | Integración API-04 + componente historial/resultado |
| AC-18 | Unit validaciones + integración mensajes por fila |
| AC-19 | Pruebas de componentes (estados, foco), prueba i18n y `i18n:check`; revisión visual en publish |
| AC-20 | Test de fronteras |

# Implementation Plan

## Architecture considerations
Ver los dos ADR. Dominio de `data_import` sin Django; puertos para las fachadas; adaptadores en `infrastructure/`; una sola vía a otros módulos: `services.py`.

## Proposed solution
Módulo `data_import` con casos de uso `UploadSalesFile`, `PreviewSalesImport`, `ExecuteSalesImport`, consultas de historial; parsers CSV/XLSX; fachadas de escritura nuevas en catalog/customers/purchases/sales; API DRF; feature Angular `features/data-import/` con asistente e historial.

## Files/components affected
- **Backend nuevo:** `backend/modules/data_import/` (`domain/` mapeo, normalización, agrupación, claves, errores; `application/` casos de uso y puertos; `infrastructure/django/` modelos, repositorios, parsers, adaptadores; `api/` vistas, serializers, urls; `tests/`), registro en `config/settings` (INSTALLED_APPS) y `config/urls.py`.
- **Backend modificado (aditivo):** `catalog/services.py`, `customers/services.py`, `purchases/services.py`, `sales/services.py` (+ ajuste en `sales/infrastructure/adapters.py` para `post_accounting=False`), `inventory/services.py` y `costing` solo si falta alguna lectura; `shared/` solo si hace falta.
- **Migraciones:** `data_import/migrations/0001_initial` (tablas nuevas).
- **Frontend nuevo:** `frontend/panel_admin/src/app/features/data-import/` (pages `sales-import`, `import-history`, `import-detail`; services; models; spec), rutas bajo `sales/import`, entrada de menú en `assets/data/routes.json`, claves `DATA_IMPORT.*` en `assets/i18n/{es,en,pt}.json`.
- **Docs:** `docs/architecture/ddd.md` §10 (mapa de dependencias y nuevo contexto), `docs/design/design-system.md` §6 (línea de menú), `CLAUDE.md` si cambian los comandos/dependencias.
- **Tests:** backend (unit, integración, fronteras), frontend (componentes y servicios).

## Implementation steps
1. **Dominio y parsers** (AC-01..03, AC-18, INV-05, INV-07): normalización, parseo, sinónimos, mapeo sugerido, agrupación en ventas, claves; parsers CSV/XLSX con límites. *[necesita `openpyxl`: confirmar antes de instalar]*
2. **Fachadas de escritura** (INV-06, INV-08, AC-07..10): catalog, customers, purchases, sales (con precio del archivo y `post_accounting`), y lecturas de inventario/costeo/cobertura; tests de integración por módulo y de fronteras (AC-20).
3. **Persistencia** (INV-05, INV-09): modelos `ImportRun`, `ImportRowResult`, `ImportedSale`, migración, repositorios, bloqueo por empresa.
4. **Casos de uso** `Upload`, `Preview`, `Execute` (INV-04, AC-06, AC-12..15): orden cronológico, faltante, transacción por venta, mapeo de errores a mensajes accionables.
5. **API** (API-01..05, AC-04, AC-16, AC-17): vistas, serializers, permisos y módulos requeridos, plantilla CSV.
6. **Frontend** (UI-01..04, AC-19): servicio de API, asistente de 4 pasos, historial/detalle, rutas, menú, i18n en tres idiomas, pruebas de componentes.
7. **Documentación y calidad:** `ddd.md`, `design-system.md`, `ruff`/`flake8` sobre lo cambiado, `npm run lint`, `npm run i18n:check`, suites completas.

## Database / migrations
Una migración nueva para las tres tablas propias (índices: `(company_id, source_key)` único en `ImportedSale`; `(run_id, row_number)` en `ImportRowResult`; `(company_id, created_at)` en `ImportRun`). No se edita ninguna migración existente. Reversible.

## Risks
- **R-01** costo/cobertura: la vista previa lo detecta y la ejecución devuelve el error del módulo por venta.
- **R-02** fechas históricas en eventos de costo e inventario: verificar `occurred_at` en entradas/salidas y `cost_*`; si no lo respetan, usar los parámetros ya existentes en `inventory/services.py` y cubrirlo con test de orden cronológico; si hace falta un cambio en otro módulo, parar y reportar (`PLAN_UPDATE_REQUIRED`).
- **R-03** irreversibilidad: confirmación, vista previa y rastro por fila.
- **R-05** tiempo de petición: límites de filas/tamaño; documentar `proxy_read_timeout` en `docs/deployment` si hiciera falta.
- **R-06** seguridad de archivos: límites de zip/filas/longitud, solo valores, tipo y extensión validados.
- **R-07** homónimos por nombre: la vista previa muestra nuevos vs existentes.

## New dependencies
- **`openpyxl`** (pura Python, lectura de `.xlsx`) en `backend/requirements/base.txt`. **Requiere confirmación del usuario antes de instalar** (regla de `CLAUDE.md`); si se rechaza, la importación aceptaría solo CSV. Frontend: ninguna.

## Changelog
_(v1: sin cambios)_
