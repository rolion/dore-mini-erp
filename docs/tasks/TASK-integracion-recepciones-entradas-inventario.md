# TASK-integracion-recepciones-entradas-inventario: Generar entradas de inventario desde recepciones (PB-INT-001)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-integracion-recepciones-entradas-inventario
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/37
**Fuente:** https://trello.com/c/y5fFL3le/17-pb-int-001-generar-entradas-de-inventario-desde-recepciones

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-10-30 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta de Trello | delivery-start |
| 2026-10-30 | INVESTIGATION → PLANNING | NEEDS_PLAN; diseño no requerido (pantallas existentes, sin patrón nuevo) | delivery-start |
| 2026-10-30 | PLANNING → ENGINEERING | Specification READY; PLAN v1 y PR | delivery-start |
| 2026-10-30 | ENGINEERING → REVIEW | Implementación completa según PLAN v1 | delivery-build |
| 2026-10-30 | REVIEW → PUBLISH | Quality Gate ciclo 1 PASS con reservas (sin Critical/High; 1 Medium y 3 Low abiertos); a la espera de aprobación humana | delivery-publish |

## Investigación

### Requerimiento
Fuente: tarjeta de Trello **PB-INT-001 · Generar entradas de inventario desde recepciones** (Integraciones, P1; dependencias PB-COM-004, PB-INV-004, PB-INV-007). Insumo, no Specification aprobada.

Como administrador, quiero que las compras recibidas incrementen el stock para evitar registrar dos veces la misma operación.

- **Superficies:** formulario y detalle de Recepción; listado/detalle de Movimientos de Inventario. Sin pantalla ni menú de integración.
- **Al revisar la recepción:** producto controlado, cantidad, unidad, almacén destino y el mensaje «Esta recepción generará entradas de inventario». Los ítems sin stock se identifican sin asignarles una entrada.
- **Detalle confirmado:** enlaces a movimientos generados con referencia y cantidad; con Inventario deshabilitado, «Recepción documental, sin movimiento de inventario».
- **Interfaz:** confirmar muestra recepción y stock actualizados; ante error no hay éxito parcial y se puede reintentar sin duplicar. **El detalle histórico conserva el modo con que se confirmó aunque cambie la configuración después.**
- **AC:** (1) con Compras e Inventario activos, una recepción genera una entrada por cada ítem que controla stock en el almacén elegido; (2) productos sin control de stock no generan movimientos y la recepción funciona con Inventario deshabilitado; (3) recepción y movimientos se confirman o fallan juntos; reintentos y confirmaciones simultáneas no duplican entradas.

### Hechos encontrados
La mayor parte de esta historia **ya existe**: PB-COM-004 (PR #33, en `main`) construyó la integración Compras→Inventario.
- `backend/modules/purchases/application/receipt_commands.py:68-95` — `RegisterReception` bloquea la compra (`for_update=True`), es idempotente por `receipt_id` y `_enter_stock` crea una entrada por línea controlada en un almacén activo, o ninguna si Inventario está apagado o no hay líneas controladas. Cubre los AC 1, 2 y 3 de la tarjeta (atomicidad por la `transaction.atomic` de `_run`; simultáneas por el bloqueo de la compra y `receipt_id`).
- `backend/modules/purchases/infrastructure/adapters.py:57-83` — `StockEntryAdapter`: `record_movement` con `source_type='purchase_receipt'`, `source_id=receipt.id`, `source_line=product_id` (idempotente en Inventario), `reference=REC-…`.
- `backend/modules/purchases/application/receipt_queries.py:101-110` — **el detalle decide el modo con el estado actual del módulo** (`self.stock.is_available()`): con Inventario apagado después, `movements = None` y se pierde el nombre del almacén; con Inventario encendido después, una recepción documental muestra «Esta recepción no movió existencias» (bloque `no-movements` de `reception-detail.component.html`). **Incumple «el detalle histórico conserva el modo con que se confirmó»**; PB-COM-004 lo dejó como EDGE-08.
- `backend/modules/purchases/infrastructure/django/models.py:72-88` — `ReceiptModel` tiene `warehouse_id` (nulo si no hubo entradas) pero no guarda el modo; `domain/receipt.py:22-39` tampoco. Migración más reciente: `0004_receipts`.
- `backend/modules/purchases/api/receipt_serializers.py:44-72` — el detalle devuelve `warehouse`, `lines` y `movements` (id, producto, almacén, cantidad, unidad; **sin referencia**). `application/ports.py:44-52` — `StockEntryMovement` no incluye `reference`, aunque `inventory.services.SourceMovement` sí la trae (`inventory/services.py:175-179`).
- La fachada `list_movements_for_source` no consulta el estado del módulo (`inventory/services.py:168-179`): el detalle puede seguir leyendo los movimientos aunque Inventario se apague. La **ruta** de Movimientos sí respondería 403 `module_disabled` con el módulo apagado.
- Frontend: el resumen avisa «Se registrará una entrada de existencias en {almacén} por cada producto con control de stock (N)» (`pages/reception-form/reception-form.component.html:174-178`), marca «Controla stock» en la línea (`:93-94`) y no tiene aviso documental. El detalle muestra la tabla de movimientos sin referencia y «Ver movimientos» filtra por `source_type`/`source_id`.

### Hipótesis / supuestos no confirmados
- **H-01** «Modo» = si Inventario estaba habilitado al confirmar: `inventory` (aunque ninguna línea fuera controlada) o `documental`. Se guarda al confirmar y no cambia.
- **H-02** Recepciones anteriores a esta task: con `warehouse_id` → `inventory`; sin él → modo desconocido (nulo) y el detalle conserva el comportamiento actual; no se inventa el histórico.
- **H-03** Con modo `inventory` el detalle sigue mostrando sus movimientos y almacén aunque Inventario se apague; «Ver movimientos» solo aparece si Inventario está habilitado ahora (la ruta destino lo exige). Con modo `documental` nunca se muestran movimientos, aunque Inventario se active después.
- **H-04** «Los ítems sin stock se identifican» = rótulo «Sin control de stock · sin entrada» en el resumen y el detalle (solo con modo `inventory`).
- **H-05** No cambian reglas de dominio, idempotencia, almacén ni el contrato de creación; el cambio es aditivo.

### Módulos y dependencias relacionadas
`purchases` (propietario del cambio). `inventory` solo por su fachada (dependencia ya permitida). Sin cambios en `inventory`, `catalog` ni `modularity`.

### Implementaciones similares existentes
`stock-output-card` y el diálogo de entrega de Ventas (`features/sales`); aún no existe un modo guardado por documento (se introduce aquí).

### Comportamiento actual
Las entradas se generan de forma atómica e idempotente, pero el modo del detalle depende de la configuración actual y faltan parte del texto/identificación pedidos (mensaje en el resumen, ítems sin stock, referencia del movimiento, texto documental).

### Restricciones
`CLAUDE.md`: no editar migraciones aplicadas (migración nueva `0005`), dominio sin Django, aislamiento por `company_id`, sin dependencias nuevas; sistema de diseño existente.

### Riesgos identificados
- Backfill de la migración: solo se deduce el modo cuando hay `warehouse_id`; el resto queda nulo.
- Si el modo se leyera del módulo vigente reaparece el defecto: debe persistirse.
- Atomicidad y simultaneidad ya tienen pruebas (AC-17 de PB-COM-004); aquí se agregan regresiones de reintento tras cambiar la configuración.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a Compras: un campo persistido (migración aditiva), un cambio de lectura y ajustes de texto; sin módulo ni dependencia nueva.

### Diseño requerido
**NO** — pantallas existentes (resumen y detalle de recepción) con ajustes de copy y una etiqueta por línea; sin patrón ni flujo nuevo. Los textos se fijan en el PLAN (UI-xx) según `design-system.md`.

## Diseño
No aplica (ver arriba).

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-10-30-integracion-recepciones-entradas-inventario.md` (v1, COMPLETO). Specification readiness: READY.

## Implementación
Implementado según PLAN v1, sin cambios de Specification.

**Backend (`purchases`)**: `InventoryMode` y `Receipt.inventory_mode` (INV-01); `RegisterReception` lo fija al registrar (`inventory` si el módulo está habilitado, aun sin líneas controladas; si no `documental`); migración `0005_receipt_inventory_mode` con backfill (con almacén → `inventory`, resto nulo; INV-04, AC-07); `GetReceipt` decide por el modo guardado y no por la configuración actual (INV-02, INV-03, AC-04, AC-05); `StockEntryMovement.reference`; el serializer expone `inventory_mode`, `inventory_available`, `lines[].stock_entry` y `movements[].reference` (API-01/02, AC-06). La idempotencia (INV-05, AC-09) y la atomicidad (AC-08) ya existían y se cubren con regresiones.

**Frontend (`features/purchases`)**: modelos/servicio/fixtures; resumen del formulario con «Esta recepción generará entradas de inventario», rótulo por línea («Entrada de stock» / «Sin control de stock · sin entrada»), aviso documental y aviso sin líneas controladas (UI-01, UI-02; AC-12); detalle con referencia por movimiento, enlace «Ver movimientos» solo con Inventario habilitado hoy, nota si está deshabilitado, nota documental y «no generó entradas» (UI-03, UI-04; AC-13, AC-14). Pantallas de referencia: las existentes de recepción (plantillas «Formulario con líneas y paso de resumen» y «Detalle»); sin componentes compartidos nuevos.

**Pruebas**: `test_receipt_application` (modo, reintento tras cambiar disponibilidad, modo desconocido), `test_receipt_api` (AC-01…AC-06, AC-09; la prueba EDGE-08 anterior se reemplazó por la nueva semántica), `test_receipt_repository` (ida y vuelta del modo y backfill) y specs Karma de formulario, detalle y servicio.

**Desviaciones**: ninguna de alcance. El enlace «Ver movimientos» de modo desconocido (`null`) sigue el comportamiento previo. Texto del resumen cuando Inventario está habilitado pero ningún producto recibido controla stock: «Esta recepción no generará entradas de inventario…» (caso no cubierto literalmente por la tarjeta).
**Deuda**: la columna Origen de Movimientos sigue sin enlace a la recepción (observación de PB-COM-004).

**Verificación propia (no es el Quality Gate)**: no hay `.env` ni PostgreSQL en este worktree (copiar el `.env` fue denegado); backend con SQLite temporal vía variables de entorno: `modules.purchases` 207 pruebas, fallan solo las 3 de concurrencia de filas que exigen PostgreSQL (preexistentes) y las de recepciones/repositorio/aplicación pasan; `makemigrations --check` sin cambios. Frontend: `ng lint` OK, `ng build` OK, Karma `features/purchases` + `features/inventory` 293/293 (se apartó temporalmente `app.component.spec.ts`, que no compila en `main`, y se restauró). Pendiente: PostgreSQL (concurrencia, AC-10) y revisión visual.

## Review
**Quality Gate ciclo 1 (subagente aislado): PASS con reservas.** Sin hallazgos Critical/High.
- Backend (SQLite temporal, sin PostgreSQL): `manage.py test modules.purchases inventory sales modularity accounts` 779 pruebas; 15 fallas, todas de SQLite o preexistentes y ninguna en recepciones (concurrencia de bloqueo de filas, unicidad sin distinguir mayúsculas, orden); las pruebas nuevas de recepciones pasan. `makemigrations --check` sin cambios; `bandit` sin hallazgos en `purchases`.
- Frontend: `ng lint` OK, `ng build` OK, Karma `features/purchases` + `features/inventory` 293/293.
- Límites DDD, migración `0005` nueva con backfill, contrato aditivo y textos de la tarjeta verificados por lectura de código.
- AC-01…AC-09, AC-11…AC-14 y AC-16 con verificación; AC-15 cubierto solo parcialmente (REV-01); AC-10 no ejecutado (exige PostgreSQL).
- No realizado: PostgreSQL, revisión visual en navegador, `npm audit`.
- Hallazgos: [REV-01](../reviews/REV-2026-10-30-integracion-recepciones-entradas-inventario-01.md) (Medium, IMPLEMENTATION: falta prueba de reintento con el mismo `receiptId` sin éxito parcial, AC-15; **resuelto** con una prueba nueva, Karma 294/294), [REV-02](../reviews/REV-2026-10-30-integracion-recepciones-entradas-inventario-02.md) (Low, ARCHITECTURE: `stock_entry` se calcula en el serializer), [REV-03](../reviews/REV-2026-10-30-integracion-recepciones-entradas-inventario-03.md) (Low, DESIGN: doble mensaje en modo documental y marca de resumen atenuada en vez de badge), [REV-04](../reviews/REV-2026-10-30-integracion-recepciones-entradas-inventario-04.md) (Low, IMPLEMENTATION: `test_receipt_domain` sin tocar e `inventory_mode` asignado sin método del agregado).

## Verificación posterior (PostgreSQL)
Con el `.env` del checkout principal copiado al worktree (por indicación del usuario; ignorado por git): suite completa del backend con PostgreSQL real, `config.settings.test`: **1141 pruebas OK** (incluye `test_receipt_concurrency`, AC-10, y las pruebas de bloqueo que fallaban en SQLite); `makemigrations --check`: sin cambios. Con esto quedan cerradas las fallas atribuidas a SQLite. La revisión visual se hizo después (sección siguiente).

## Seguimiento tras el Quality Gate (hallazgos Low)
REV-02 (`stock_entry` a `ReceiptDetail`), REV-03 (badge; el doble mensaje no se reproducía, se fijó con una prueba) y REV-04 (`Receipt.set_inventory_mode` + pruebas de dominio) resueltos. Backend `modules.purchases` con PostgreSQL: 216 OK; Karma purchases+inventory 294/294; `ng lint` y `ng build` OK.

## Revisión visual (navegador, 2026-10-30)
Backend y frontend de este worktree contra PostgreSQL local (migración `0005` aplicada), empresa de prueba «Visual PB-INT-001» con Inventario y Compras habilitados, un producto controlado (Harina) y uno sin control (Bolsa). Escritorio 1440 px y móvil 375 px.
- **Resumen (con Inventario):** «Esta recepción generará entradas de inventario…», badge verde «Entrada de stock» en Harina y «Sin control de stock · sin entrada» en Bolsa, almacén destino. OK.
- **Confirmar:** toast «Recepción REC-… registrada», vuelta a la pestaña Recepciones con Recibida/Pendiente y estado «Recibida parcialmente». OK.
- **Detalle (con Inventario):** almacén, productos, «Sin control de stock · sin entrada» en la línea sin stock, tabla de movimientos con Referencia, botón «Ver movimientos». OK.
- **Inventario deshabilitado después:** el mismo detalle conserva almacén y movimientos, sin botón «Ver movimientos» y con «Inventario está deshabilitado; los movimientos se muestran sin enlace». OK (INV-02/03).
- **Recepción documental (Inventario apagado):** el resumen muestra «Recepción documental, sin movimiento de inventario»; en BD `inventory_mode = documental`, sin almacén.
- **Detalle documental con Inventario reactivado, móvil:** un único mensaje «Recepción documental, sin movimiento de inventario», sin movimientos ni scroll horizontal de página. OK.
- **No verificado:** tema oscuro de la plantilla (la emulación `prefers-color-scheme` no activa el tema de Oreva, que usa su propio interruptor); la columna Origen de Movimientos (deuda previa) y el filtro por recepción solo por pruebas.
Los datos de prueba quedaron en la base local (empresa «Visual PB-INT-001», usuario `visual_pbint`) y el almacén predeterminado se creó al listar almacenes.

## Publicación
PR [#37](https://github.com/rolion/dore-mini-erp/pull/37) listo para aprobación humana (no se mergea automáticamente). Cambio sensible: **base de datos** (migración aditiva `0005` con `RunPython` de backfill, sin ADR). Verificado en PostgreSQL y en navegador; solo falta la aprobación humana del merge.
