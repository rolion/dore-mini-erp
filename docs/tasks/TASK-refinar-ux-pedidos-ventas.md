# TASK-refinar-ux-pedidos-ventas: Refinar la experiencia de Pedidos (lista y detalle) en Ventas

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-refinar-ux-pedidos-ventas
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/57

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN | Pantallas afectadas, diseño requerido | delivery-start |
| 2026-11-04 | DESIGN → PLANNING | DDR propuesto; Specification READY | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Plan v1 y PR | delivery-start |
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-04 | REVIEW → PUBLISH | Quality Gate PASS con 2 observaciones Low | delivery-publish |

## Investigación

### Requerimiento
Fase de refinamiento del módulo Ventas, vista Pedidos. Se pide mejorar UX/UI de la lista, el alta y el detalle. Insumo: crítica de diseño previa (sesión 2026-11-04) con 13 capturas (lista, alta vacía y llena, detalle en estados Nuevo, En preparación, Listo, Pagado pendiente de entrega, modal de entrega y Entregado). La crítica no es una Specification aprobada; este task selecciona de ella lo que es solo presentación.

Decisión de alcance (criterio del agente, sin decisión de negocio abierta): **solo frontend de `features/sales`**; sin cambios de API, dominio ni migraciones. Quedan fuera lo que exige backend o una regla de negocio (ver «Out of scope» del PLAN).

### Hechos encontrados
- `frontend/panel_admin/src/app/features/sales/pages/order-detail/order-detail.component.html:49-125` — el detalle apila: tarjetas Entrega/Cobro, «Datos del pedido», salida de inventario, y después Productos, Importes y Pagos. El total solo aparece en «Importes» (`order-summary.component.html:30`), debajo de Productos.
- `…/order-detail.component.html:81-88` — con `hasBalance` falso muestra «Sin saldo» en verde (`text-success`), también cuando el pedido no tiene líneas y el total es `0.00` (`models/order.ts:360-362`: `hasBalance` solo compara `balance !== '0.00'`).
- `…/order-payments.component.html:4-6` — «Registrar pago» vive en la cabecera de la tarjeta Pagos, la última del detalle; `open()` es método del componente (`:5`), la tarjeta Cobro (`order-detail.component.html:73-92`) no tiene acción.
- `…/order-payments.component.html:66` — la fecha del pago se imprime cruda (`{{ payment.paymentDate }}` → `2026-11-04`); el resto del detalle usa `date: 'dd/MM/yyyy'` (`order-detail.component.html:61,116`). `design-system.md` §1 exige `dd/MM/yyyy`.
- `…/order-detail.component.html:96-102` y `order-summary.component.html:21-22`, `order-items.component.html:26-27`, `order-payments.component.html:5,46` — «Editar datos», «Aplicar», «Agregar», «Registrar pago» y «Registrar» son todos `btn-primary`; junto a la acción de estado (`order-detail.component.html:19-20`, `btn-primary`) compiten hasta 3 botones primarios sólidos en la misma vista.
- `…/order-detail.component.html:119-122` — «Creado» y «Última actualización» ocupan filas completas del `dl` con el mismo peso que Cliente y Canal.
- `order-items.component.html:6-30` + `order-detail.component.html:131` — con `items.length === 0` el buscador de producto no recibe foco y el texto de ayuda queda debajo (`:76`); el formulario de alta navega al detalle al guardar (`order-form.component.ts:151,205`).
- `order-list.component.html:103-108` — la columna «Pedido» muestra la fecha como enlace en negrita y el código (`row.code`) como `small.text-muted`; el código es lo que identifica el pedido (`models/order.ts:102`).
- `…/order-list.component.html:43-98` — 7 controles de filtro en dos filas siempre visibles (entrega, pago, canal, cliente, fecha de, desde, hasta) además de los atajos (`:33-41`), que ya cubren Pendientes/Por cobrar/Entregados/Cancelados.
- `…/order-list.component.html:100-158` — solo el enlace de la columna Pedido y el icono «ojo» navegan al detalle; la fila no es clicable.
- `backend/modules/sales/domain/order.py:254-255` — `editable` es `status in OPEN_STATUSES`: las líneas se editan en Nuevo, En preparación y Listo aunque el pedido esté pagado. Es regla del servidor (`models/order.ts:121`: «la interfaz no replica las reglas de estado»).
- `backend/modules/sales/api/` — la lista de pedidos no tiene parámetro de búsqueda de texto (solo `status`, `payment_status`, `sales_channel`, `customer_id`, fechas, `has_balance`, `ordering`: `models/order.ts:200-213`).
- `docs/design/design-system.md` §3-§5 — plantillas Lista y Detalle, botones (una acción principal por pantalla; secundaria `btn-light`), badges y estados; el sistema documenta «Alta rápida» con icono «+» (icon-only).

### Hipótesis / supuestos no confirmados
- El fondo azul claro de los inputs y el índigo del botón «Marcar listo» en las capturas no están en las plantillas de los componentes (todos usan `form-control`/`btn-primary`): vienen del tema/skin o del autocompletado. No se tocan; se verifica en el build.
- Los textos pequeños (≈11-12 px) del detalle en las capturas parecen escala del navegador; el CSS de la lista solo fija `0.8rem` en la regla móvil (`order-list.component.scss:5`). No se cambia tipografía global.
- «Almacén de salida» sin control visible en el modal de entrega (captura): el código sí renderiza un `select` (`delivery-dialog.component.html:22-28`); con un solo almacén probablemente la plantilla lo muestra como texto plano. Se verifica en el build.

### Módulos y dependencias relacionadas
Solo `sales` (frontend `features/sales`) y `src/assets/i18n/{es,en,pt}.json`. Sin otros módulos.

### Implementaciones similares existentes
`features/customers/pages/*` (perfil de cliente con cifras, TASK-mejorar-perfil-de-cliente) y `features/products/pages/product-detail` (TASK-mejorar-ux-catalogo-productos-servicios): resumen por cifras sobre `dl` secundario y metadatos al pie en `small.text-muted`.

### Comportamiento actual
Ver «Hechos encontrados».

### Restricciones
- Sin cambios de API, dominio ni migraciones.
- Sin texto hardcodeado: claves en `es/en/pt` (`npm run i18n:check`).
- Los `data-testid` existentes se conservan (las pruebas los usan).
- REQ-SAL-016 (entregado ≠ pagado, pagado ≠ entregado): los avisos de `order-detail.component.html:38-47` se conservan.

### Riesgos identificados
- Mover «Registrar pago» a Cobro cambia quién abre el formulario: hay que comunicar los dos componentes sin duplicar estado.
- Reordenar tarjetas puede romper pruebas que dependen del orden (`order-detail.component.spec.ts`).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a un módulo, solo presentación, sin decisión arquitectónica nueva.

### Diseño requerido
**SI** — reordena la jerarquía de la pantalla de detalle y compacta la lista; hay riesgo de inconsistencia con el sistema de diseño.

## Diseño
Ver `docs/design/DDR-refinar-ux-pedidos-ventas-lista-y-detalle.md`.

## Arquitectura
No aplica según veredicto.

## Plan
Ver `docs/plans/PLAN-2026-11-04-refinar-ux-pedidos-ventas.md` (v1, COMPACTO, READY).

## Implementación
Solo frontend de `features/sales` y `assets/i18n/{es,en,pt}.json`; sin cambios de API, dominio ni migraciones.

- **AC-01** `order-detail.component.html`: orden Entrega/Cobro → Productos → Importes → Pagos → Salida de inventario → Datos del pedido; «Creado/Última actualización» en `small.text-muted` (`data-testid="audit"`).
- **AC-02** `order-detail.component.ts`: `openPayment()` (`viewChild` a `OrderPaymentsComponent`: abre el formulario, scroll y foco al monto) y botón `pay-action` en Cobro, solo con `canRegisterPayment`.
- **AC-03** Cobro con `items.length === 0` muestra «Sin productos» atenuado y no ofrece pago.
- **AC-04** «Editar datos», «Aplicar» y «Agregar» pasan a `btn-outline-primary`.
- **AC-05** Fecha de pago con `date: 'dd/MM/yyyy'` (`order-payments`, importa `DatePipe`).
- **AC-06** Ya existía: `removeItem` pide confirmación con `confirmRemove` (`order-detail.component.ts`) y la prueba «removes an item only after confirming (AC-05)». Sin cambios.
- **AC-07** `order-items.component.ts`: `effect` que enfoca el buscador una vez si el pedido es editable y no tiene líneas.
- **AC-08/AC-09** `order-list`: código como enlace principal con fecha debajo; `onActivate` navega al detalle al hacer clic en la fila (ignora clics en enlaces/botones); «Más filtros» (canal, fecha de, desde, hasta) con `aria-expanded`, abierto si hay filtro secundario activo.
- **AC-10** Claves nuevas en las tres lenguas: `SALES.ORDER_DETAIL.SIN_PRODUCTOS`, `…AGREGUE_PRODUCTOS_PARA_COBRAR`, `SALES.ORDER_LIST.MAS_FILTROS`.

**Pantallas de referencia:** plantillas Detalle y Lista de `design-system.md` §5 (`product-detail`/`product-list`). **Componentes compartidos:** `money`, badges existentes; no se creó ninguno.

**Desviaciones respecto al plan:** AC-06 no requirió código (ya implementado). Dos specs existentes se ajustaron por cambio intencional: clase del botón «Agregar» y formato de fecha de pagos; el spec de la lista abre «Más filtros» antes de leer las opciones de canal.

**Verificación propia (no es el Quality Gate):** `ng test` de `features/sales` 212 pruebas OK; `npm run lint`, `npm run i18n:check` y `npm run build` sin errores. Para correr las pruebas en este worktree se enlazó `node_modules` del checkout principal con una *junction* (no versionada; sin instalar dependencias). Una prueba de `order-list-filters.spec.ts` falló una vez de forma intermitente en una corrida y pasó en las siguientes; no depende de este cambio.

**Deuda / hipótesis sin verificar visualmente:** fondo azul de inputs, índigo de «Marcar listo» y tamaño de texto del detalle (tema/skin; no se tocaron); «Almacén de salida» en el modal de entrega. No se probó en navegador.


## Review
**Veredicto: PASS** (Quality Gate en subagente aislado, 2026-11-04). Sin hallazgos Critical/High.
- `ng test` completo: 1247 OK, 1 fallo preexistente en `main` (`screens-i18n.spec.ts:60`, dependiente del orden/idioma; reproducido en `origin/main`, la rama no toca ese spec). `npm run lint` OK, `npm run i18n:check` 0 faltantes, `npm run build` OK, `npm audit --omit=dev` 0 vulnerabilidades. Backend sin cambios (no se corrió).
- AC-01..AC-10 cubiertos (AC-06 ya existía).
- Hallazgos Low abiertos: [REV-01](../reviews/REV-2026-11-04-refinar-ux-pedidos-ventas-01.md) (`aria-controls` apunta a un id que solo existe con el panel abierto), [REV-02](../reviews/REV-2026-11-04-refinar-ux-pedidos-ventas-02.md) (`setTimeout` sin cancelar; dependencia del id `#payment-amount`).
- Consistencia visual: **no verificada** en navegador (solo código y diff).

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/57 listo para aprobación humana; no se mergea. Sin cambio sensible (sin ADR, auth, base de datos ni infraestructura).
