# DDR-configurar-asientos-automaticos-modulo-panel-cuentas-por-evento: Panel «Asientos automáticos» con vista previa Debe/Haber en cada módulo

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-asientos-automaticos-modulo
**Fecha:** 2026-11-16

## Contexto
La configuración de cuentas por evento vive en el módulo de origen (decisión de la persona y de CONT-11). Hay que ofrecer **un único componente** reutilizable, con el mismo contrato en Ventas, Compras, Inventario y Gastos, que muestre solo los eventos de su módulo, deje elegir cuentas con la clasificación correcta y enseñe el asiento Debe/Haber resultante. Los módulos todavía no contabilizan: el panel debe explicarlo sin prometer lo que aún no ocurre y sin alarmar si Contabilidad está deshabilitada.

## Pantallas/flujos afectados
- **Ventas, Compras, Inventario** (`/sales/settings`, `/purchases/settings`, `/inventory/settings`, página `module-settings` con pestañas «General» e «Historial de cambios»): nueva pestaña **«Asientos automáticos»**.
- **Gastos**: no tiene pantalla de configuración. Nueva ruta `/expenses/settings` («Configuración» en el submenú de Gastos) con la misma pestaña, como única pestaña de contenido de la página.
- Cobros/Servicios: sin pantalla en esta tarea (el catálogo backend ya contiene sus eventos).
- La persona entra a la pestaña, elige cuentas y ve cómo queda cada asiento; no confirma nada irreversible.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (`design-system.md` §5, referencia `features/inventory/pages/inventory-configuration` y la pestaña `methods-tab` existente), sin componente nuevo de la plantilla Oreva. Un solo componente compartido `app-posting-config-panel` (`@Input() module`) en `features/accounting/components/`:
1. **Aviso de estado** arriba (`alert`, patrón tenue admitido):
   - Contabilidad deshabilitada: `alert-info` tenue «Contabilidad no está habilitada. Puede dejar esta configuración preparada; no se generan asientos mientras esté deshabilitada» (no se exige configurar nada).
   - Contabilidad habilitada y faltantes: `alert-warning` «Falta configurar N cuentas. Las operaciones de este módulo no se podrán confirmar hasta completarlas», con la lista de faltantes y enlace al ancla de cada fila.
   - Todo listo: `alert-success` tenue «Configuración completa».
   - Texto fijo `small.text-muted`: «Los cambios aplican solo a operaciones nuevas; los asientos ya registrados no se modifican.»
2. **Sección «Cuentas»**, una fila por rol del módulo: etiqueta del rol (p. ej. «Cuentas por cobrar»), `select` con las cuentas de la clasificación requerida (activas; carga con `GET accounts/?is_active=true&account_class=<X>`), pista bajo el campo «Cuenta de Activo» / «Cuenta de Ingresos»…, botón «Guardar» por fila y estado de la fila (`Guardado ✓`, error del servidor bajo el campo con `role="alert"`). Un rol compartido (Inventario en Compras e Inventario) lo indica con `small.text-muted` («Se comparte con Compras»).
3. **Sección «Cuentas de cobro/pago por método»** (solo si hay eventos con método: Ventas, Compras, Gastos): tabla Método | Cuenta (Caja/Banco de Activo) con el mismo `select` y `small.text-muted` «El método de pago no es una cuenta: elija dónde entra o sale el dinero». Edita el mapeo existente de la empresa (se comparte entre módulos).
4. **Sección «Cuenta de gasto por categoría»** (solo Gastos): tabla Categoría | Cuenta de Gastos; categorías inactivas atenuadas; vacío con enlace «Crear categoría».
5. **Sección «Asientos previstos»**: por evento una tarjeta con título («Reconocer venta», «Cobro de venta»…) y una tabla de dos filas **Debe | Haber** (columna Cuenta con «código · nombre», o «Sin configurar» en `text-warning` con texto, o «Según el método de pago» / «Según la categoría» en `text-muted`); `aria-label` por tabla. La vista previa se recalcula en vivo al elegir una cuenta, antes de guardar.
6. Enlace «Administrar cuentas» a `/accounting/accounts` si la empresa no tiene cuentas de la clasificación requerida (el `select` vacío se explica: «No hay cuentas de Ingresos activas»).

## Alternativas consideradas
- **Pantalla única en Contabilidad:** descartada por la persona.
- **Un formulario distinto por módulo:** más fiel a cada pantalla pero cuatro implementaciones; un componente con `@Input() module` mantiene una sola verdad (mismos mensajes y vista previa).
- **Diálogo por evento en lugar de filas editables:** más pasos para configurar 3-5 cuentas; la edición por fila con vista previa inmediata es más corta.
- **`ng-select` con búsqueda:** innecesario con pocas cuentas por clasificación; `select` nativo como en el resto de Contabilidad.

## Comportamiento por privilegio/estado
- **Cargando:** esqueleto simple («Cargando…»). **Error de carga:** `alert-danger` con «Reintentar». **Vacío:** el módulo sin eventos no muestra la pestaña.
- **Guardado:** fila con «Guardando…» y «Guardado ✓»; error 400 bajo el campo (cuenta de otra empresa, deshabilitada o clasificación inválida) sin perder la selección; error 5xx con «Reintentar».
- **Permisos:** solo el administrador de la empresa (el servidor lo impone; el frontend no es la barrera). El servidor valida empresa, cuenta activa y clasificación en cada guardado.
- **Foco/teclado:** `label` asociada a cada `select`; tras guardar, el foco queda en el campo; el primer error recibe foco.
- **Móvil (375 px):** filas apiladas (etiqueta, `select`, botón); tablas Debe/Haber con scroll horizontal contenido (`table-responsive`); sin texto cortado.
- **Tema oscuro:** solo clases de texto/fondo de Bootstrap (`text-body-secondary`, `bg-*-subtle`), sin colores HEX.
- **Textos:** todo con claves `ACCOUNTING.POSTING.*` en es/en/pt (sin texto hardcodeado).

## Consecuencias
- El panel vive en `features/accounting` y lo importan cuatro features: acoplamiento de UI aceptado por ser el contrato común (ADR); si crece, puede moverse a `shared/components`.
- Gastos gana una ruta y un ítem de menú «Configuración» nuevos (`routes.json`, i18n).
- Hasta que VEN-01/COM-01/INV-01/gastos contabilicen, el panel configura cuentas que aún no se usan; el aviso lo explica. Deuda visual: «Cobros/Servicios» sin host.
- **Actualización propuesta de `design-system.md` §5/§6:** añadir «Panel de cuentas por evento con vista previa Debe/Haber» (patrón anterior) y los ítems «Configuración» de Gastos y la pestaña «Asientos automáticos» de Ventas, Compras e Inventario.
