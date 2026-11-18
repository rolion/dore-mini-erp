# DDR-categorias-gastos-clasificacion-egreso-pestana-egresos: Pestaña «Egresos» y clasificación visible en el gasto

**Estado:** Propuesto
**Task relacionado:** TASK-categorias-gastos-clasificacion-egreso
**Fecha:** 2026-11-15

## Contexto
La persona administradora debe indicar una vez qué clasificación de egreso corresponde a cada categoría de Gastos y a los pagos a proveedores, y ver qué falta antes de registrar operaciones. Contabilidad → Configuración ya agrupa Cuentas, Métodos, Clasificaciones y Corte (`features/accounting/pages/accounting-settings`).

## Pantallas/flujos afectados
- **Contabilidad → Configuración, pestaña nueva «Egresos»:** una fila por categoría de Gastos activa (nombre, selector de clasificación de egreso, estado «Configurada» / «Pendiente» / «Inactiva») y una fila fija «Pagos a proveedores» con el mismo selector. Cada fila guarda al cambiar el selector (toast de éxito; error inline por fila). Opción «Sin clasificación» para quitarla.
- **Detalle del gasto:** línea «Clasificación» (nombre, o «Sin clasificación» para gastos anteriores).
- **Formulario de gasto y de pago de compra:** si la API responde `classification_not_configured` o `classification_invalid`, el error del campo/formulario muestra el texto y un enlace «Configurar en Contabilidad → Egresos».

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (`docs/design/design-system.md`, sección 5; referencia `classifications-tab`) con tabla responsiva, badges de estado de la sección 3 y `form-select` nativo como en el diálogo de cuenta; sin diálogo (edición en línea porque cada fila tiene un único campo). Sin componentes nuevos de Oreva.

## Alternativas consideradas
- **Selector dentro del diálogo de categoría (módulo Gastos):** deja la configuración contable repartida y no cubre «Pagos a proveedores»; se prefiere un solo lugar de configuración contable.
- **Pestañas separadas para Gastos y Compras:** dos pantallas para dos filas conceptuales; una pestaña basta.
- **Botón «Guardar» por pantalla:** más pasos y estados parciales; se guarda por fila.

## Comportamiento por privilegio/estado
Estados: cargando, vacío («Aún no hay categorías de gastos»), error con reintento, éxito por toast. Si el módulo Gastos o Compras está deshabilitado su parte muestra el aviso estándar de módulo no habilitado, y el resto sigue disponible. Los selectores solo ofrecen clasificaciones `EXPENSE` activas (la asociada inactiva se muestra marcada «Inactiva»). Solo administradores de empresa llegan a esta pantalla; **el backend valida permisos, empresa, dirección y estado**, el frontend no es la barrera.

## Consecuencias
Sin deuda visual nueva. Textos en es/en/pt con las mismas claves. Los formularios de Gastos/Compras ganan un enlace de ayuda; la configuración desde la propia categoría queda fuera de esta tarea.
