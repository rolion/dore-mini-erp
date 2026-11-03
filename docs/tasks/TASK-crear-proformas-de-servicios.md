# TASK-crear-proformas-de-servicios: PB-COT-001

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-crear-proformas-de-servicios (basada en `task/TASK-agendar-y-gestionar-citas`, PR #50, por indicación del usuario)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/52
**Fuente:** https://trello.com/c/qMQgQ0CR

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Task creado desde tarjeta Trello | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Pantallas nuevas (lista, formulario, detalle) | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Nuevo bounded context, módulo habilitable y migración | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | ADR y DDR escritos | delivery-start |
| 2026-11-03 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |

## Investigación

### Requerimiento
[PB-COT-001 · Crear proformas de servicios con líneas y precios congelados](https://trello.com/c/qMQgQ0CR) (lista «Backlog — Fase 1», orden 06 de 16, P1). **Insumo funcional, no Specification aprobada por el usuario.** Sin etiquetas, checklists ni comentarios. Aclaración del usuario: usar como base la rama del PR #50 (`task/TASK-agendar-y-gestionar-citas`).

Resumen fiel de la tarjeta:
- Historia: el operador elabora proformas de servicios para presentar precios y condiciones trazables al cliente.
- Dependencia obligatoria PB-SRV-001 (catálogo de servicios, ya en main). Clientes existe; se puede cotizar sin odontograma ni plan clínico. Un consultorio por empresa; sin Sucursales ni reserva de recursos.
- Menú/vistas: Cotizaciones → Proformas: listado, nuevo borrador, edición y detalle de versiones. Filtros por cliente, fecha y estado; columnas número/versión, cliente, fecha, total propuesto, estado.
- Campos: cliente y fecha; número generado por empresa y versión; vigencia opcional; moneda BOB; condiciones/notas comerciales. Líneas: servicio, descripción congelada, cantidad > 0, precio unitario ≥ 0, subtotal; vínculo opcional a tratamiento y pieza como referencia autorizada. Total calculado; estado.
- Acciones: agregar/quitar líneas, guardar borrador. Capturar precio/nombre al incorporar el servicio; editar precio solo con permiso. El servidor recalcula subtotales y total. Presentar exige ≥ 1 línea válida. No mueve stock ni genera venta, cuenta por cobrar o pago. Separar total propuesto de total aceptado.
- Interfaz: selector muestra servicio y precio; tabla editable con subtotales y total a dos decimales; borrador indica cambios sin guardar y errores por línea; detalle muestra versión y referencias sin exponer notas clínicas a caja.
- Criterios: servicios de 100 y 150 → total 250; cambiar el catálogo después no altera la proforma; cantidad 0 o precio negativo se rechaza; guardar repetidamente no genera obligaciones de cobro.
- Reglas transversales: respetar módulos habilitados, empresa de sesión y permisos; reutilizar componentes de PocketBiz; estados cargando/vacío/error/éxito; conservar datos ante fallos; impedir doble envío; teclado; confirmar acciones irreversibles; backend es la autoridad.

Los documentos de historias y especificaciones de Google Docs enlazados **no fueron accesibles** (HTTP 401); el análisis se apoya en la tarjeta, el código y los documentos del repositorio.

### Hechos encontrados
- `backend/modules/service_catalog/services.py:25-37` — fachada `get_service` / `get_service_for_new_use(company_id, service_id)` devuelve `ServiceSnapshot` inmutable (nombre, código, precio base, duración, activo); exige módulo `services` habilitado; ya prevista para PB-COT-001 (`docs/adr/ADR-administrar-catalogo-servicios-contexto.md`, sección Decisión).
- `backend/modules/customers/services.py:20-34` — `get_customer_for_sale(company_id, customer_id)` devuelve `CustomerForSale(id, name, active)`; `get_customer_names` para listas sin N+1.
- `backend/modules/agenda/models.py:39-53` — patrón de citas: snapshots (`customer_name`, `service_name`, `duration_minutes`) y `treatment_item_id` nulo «reservado para el futuro módulo de tratamientos; hoy no se valida ni se expone».
- `backend/modules/agenda/infrastructure/adapters.py:1-5` — los consumidores importan fachadas ajenas solo desde un adaptador de infraestructura.
- `backend/modules/sales/tests/test_boundaries.py:13-30` — mapa `ALLOWED_DEPENDENCIES` y `CONSUMERS`; todo módulo nuevo debe declararse.
- `backend/modules/modularity/domain/modules.py:19-35` — catálogo de módulos habilitables (`services` requiere `catalog`; `agenda` requiere `personnel`); no existe módulo de cotizaciones.
- `backend/config/permissions.py:21-39` — `CompanyModulePermission` exige `required_modules` en cada vista y lanza `module_disabled`; `backend/modules/accounts/api/permissions.py:15-25` — el único rol existente es `admin`; no hay permisos finos.
- `backend/config/urls.py:11-32` — rutas por módulo bajo `/api/…`; no hay `proformas`/`quotations`.
- `backend/modules/service_catalog/infrastructure/django/models.py:6-30` — dinero `DecimalField(12,2)` con `CheckConstraint`, `company_id` indexado, UUID como PK.
- `backend/modules/service_catalog/api/views.py:15-30` — paginación estricta reutilizable como patrón (valida `page`, `page_size`).
- `frontend/panel_admin/src/app/app.routes.ts:30-84` — rutas con `data: { module }` y `moduleGuard`; `frontend/panel_admin/src/assets/data/routes.json:338-363` — menú Agenda con submenú; módulo en el nodo.
- `frontend/panel_admin/src/app/features/services/` y `features/agenda/pages/appointment-*` — referencias de lista, formulario y detalle con servicios API tipados.
- `docs/design/DDR-agendar-y-gestionar-citas-pantallas-citas.md` — referencia de diseño de lista con filtros, formulario, detalle y diálogos con motivo.
- Búsqueda de `proforma|quotation|cotiz` en `backend/` y `frontend/panel_admin/src/app/`: sin implementaciones previas.
- `git`: la rama de trabajo se creó desde `origin/task/TASK-agendar-y-gestionar-citas` (07d0202), no desde `main`. Nada de la implementación de citas es requerido por proformas, pero comparte `routes.json`, `app.routes.ts`, i18n y `ALLOWED_DEPENDENCIES`.

### Hipótesis / supuestos no confirmados
- **Versiones**: la tarjeta pide «versión» y «detalle de versiones» sin definir cuándo nace una. Se asume: editar un borrador lo modifica en sitio; una proforma **presentada** es inmutable y «Crear nueva versión» copia sus líneas a un borrador con el mismo número y versión + 1, dejando la anterior como **reemplazada** al presentar la nueva. Confirmable sin bloquear.
- **Estados** de esta historia: `draft`, `presented`, `superseded`. «Aceptada/rechazada/vencida» y el **total aceptado** pertenecen a una historia posterior; aquí el total aceptado se modela como columna nula no expuesta para mantener la separación.
- **Permiso de precio**: solo existe el rol `admin`; «con permiso» se implementa como una función de política en el backend (`can_edit_price(user)`) que hoy equivale a admin (mismo criterio que `has_clinical_access`), de modo que un rol futuro sin permiso reciba 403 sin tocar la API.
- **Tratamiento y pieza**: no existe módulo de tratamientos ni odontograma. Se reserva `treatment_item_id` (UUID nulo) y `piece` (texto corto vacío) en la línea, sin validación ni entrada en la UI; el detalle los muestra si existen. «Referencia autorizada» se interpreta como validar autorización/empresa cuando exista el módulo.
- **Notas clínicas a caja**: la proforma solo tiene condiciones comerciales; no hay notas clínicas ni rol caja hoy. Se documenta que las notas son comerciales y el aviso «No incluyas diagnósticos».
- **Numeración**: consecutivo por empresa (`PRO-000001`), sin huecos garantizados bajo concurrencia mediante contador con bloqueo.
- **Cantidad**: decimal con hasta 2 decimales (0 < q ≤ 9999.99); subtotal redondeado a 2 decimales (`ROUND_HALF_UP`).

### Módulos y dependencias relacionadas
Nuevo contexto `quotations` → consume `service_catalog` (servicio y precio vigentes) y `customers` (cliente activo y nombre) solo por fachadas. Registro en `modularity` (clave `quotations`, requiere `services` y `customers`). Sin dependencia con `sales`, `inventory`, ni `agenda`.

### Implementaciones similares existentes
Citas (snapshots + historial + acciones de ciclo de vida), pedidos (`sales`: líneas con snapshot de producto/precio, `domain/order.py:139`), compras en borrador (lista/formulario/detalle).

### Comportamiento actual
No hay forma de cotizar servicios; los pedidos solo manejan productos y mueven stock al entregar.

### Restricciones
`CLAUDE.md`: dinero `Decimal`, aislamiento por `company_id`, dominio sin Django, estados por métodos del agregado, no editar migraciones aplicadas, avisar de dependencias nuevas (ninguna prevista), módulos solo por fachadas.

### Riesgos identificados
Conflictos de fusión en `routes.json`, `app.routes.ts`, i18n y `test_boundaries.py` con la rama base; numeración bajo concurrencia; precio enviado por el navegador; edición concurrente de un mismo borrador; ambigüedad de «versión».

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — nuevo bounded context y módulo habilitable, migración nueva, dependencia de dos módulos, reglas de dinero y de congelación de precios.

### Diseño requerido
**SI** — tres pantallas nuevas con tabla editable de líneas y flujo de versiones.

## Diseño
Ver [DDR-crear-proformas-de-servicios-pantallas-proformas](../design/DDR-crear-proformas-de-servicios-pantallas-proformas.md).

## Arquitectura
Ver [ADR-crear-proformas-de-servicios-contexto-congelacion-y-versiones](../adr/ADR-crear-proformas-de-servicios-contexto-congelacion-y-versiones.md).

## Plan
[PLAN-2026-11-03-crear-proformas-de-servicios](../plans/PLAN-2026-11-03-crear-proformas-de-servicios.md) v1 · COMPLETO · Specification readiness: READY (supuestos no bloqueantes listados arriba y en el plan).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
