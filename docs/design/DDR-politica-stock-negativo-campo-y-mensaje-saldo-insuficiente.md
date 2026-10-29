# DDR-politica-stock-negativo-campo-y-mensaje-saldo-insuficiente: Campo «Permitir stock negativo» y mensaje de saldo insuficiente

**Estado:** Propuesto
**Task relacionado:** TASK-politica-stock-negativo
**Fecha:** 2026-10-29

## Contexto
La historia pide un campo de configuración con confirmación al habilitarlo y, ante saldo insuficiente, mostrar producto, almacén, cantidad solicitada y existencia actual sin perder los datos del formulario. Ya existen la pantalla genérica de configuración por módulo (`ModuleSettingsComponent`, ruta `inventory/settings`, pestañas General e Historial) y el diálogo de confirmación de módulos.

## Pantallas/flujos afectados
1. **Inventario → Configuración → General** (`inventory/settings`): nuevo campo.
2. **Formulario de ajuste** (`adjustment-form`): estado de error 409 `insufficient_stock` (no ocurre por conteo, pero el contrato es común y debe verse bien si lo devuelve el servidor).
3. Confirmación de entrega y reversión de recepciones: **no existen en la UI**; quedan para PB-INV-008 y la historia de entrega con stock, que reutilizarán el componente de mensaje definido aquí.

## Componentes/patrones elegidos
- **Campo booleano** en la plantilla Formulario (`design-system.md`, sección 5) dentro de `module-settings`: `form-check form-switch` de Bootstrap con la etiqueta «Permitir stock negativo» (negrita, como los demás campos), descripción debajo (`form-text text-muted`) y «Valor predeterminado: Bloqueado» con «Restablecer» (mismo bloque que choice/percent). Tipo nuevo `boolean` en el modelo `SettingKind`.
  Descripción: «Si está desactivado (recomendado), no se confirman entregas, ajustes ni reversiones de recepciones que dejen la existencia de un producto por debajo de cero. Si lo activa, esas operaciones se permiten y pueden existir saldos negativos.»
- **Confirmación al habilitar**: al pulsar «Guardar cambios» con el interruptor pasando de desactivado a activado, se abre el diálogo reutilizado `ModuleConfirmDialogComponent` (título «Permitir stock negativo», texto «Podrán existir saldos negativos: las salidas se registrarán aunque no haya existencias suficientes. Podrá volver a bloquearlo, pero los saldos negativos ya creados no se corrigen solos.», botones «Permitir» / «Cancelar»). Cancelar deja el interruptor activado y el formulario sin guardar; deshabilitar guarda sin diálogo.
- **Mensaje de saldo insuficiente**: bloque `alert alert-danger` (patrón de error de formulario ya usado en `adjustment-form`, `conflictMessage`) con el texto «No hay existencia suficiente.» y una lista `dl` compacta: Producto, Almacén, Cantidad solicitada, Existencia actual (con la abreviatura de la unidad). Es un componente `insufficient-stock-alert` reutilizable en `features/inventory/components/`. No cierra ni limpia el formulario; el foco pasa al aviso (`role="alert"`).
- Sin cambios de tokens ni de `design-system.md`: se usan switch, alert y diálogo existentes.

## Alternativas consideradas
- **Casilla (`form-check`)** en lugar de interruptor: igual de simple, pero el interruptor comunica mejor un estado activado/desactivado; coste equivalente.
- **Select «Bloquear / Permitir»**: reutiliza el control choice sin tipo nuevo, pero la elección «Sin predeterminado» del select choice no encaja y el pedido habla de un campo activable.
- **Mensaje solo como texto en `conflictMessage`**: menos código, pero no cumple mostrar los cuatro datos de forma legible.

## Comportamiento por privilegio/estado
- Solo el administrador de la empresa cambia el ajuste y solo con el módulo Inventario habilitado: lo **valida el backend** (PB-CFG-001, 409 `ModuleDisabled`); el frontend no es la barrera.
- Estados del campo: cargando (spinner de la pantalla), error de carga con «Reintentar», guardando (botones deshabilitados), error de validación junto al campo, éxito con aviso, aviso al salir con cambios sin guardar (ya existente).
- Estado del mensaje: aparece solo tras un 409 `insufficient_stock`; se oculta al reintentar o al editar un campo.
- El backend aplica la política en toda salida, con independencia de lo que muestre la UI.

## Consecuencias
- Hasta PB-INV-008 y la historia de entrega con stock, el mensaje solo aparece en flujos que hoy puedan devolver `insufficient_stock` (apertura/ajuste); no hay pantallas de entrega ni reversión que se queden inconsistentes porque aún no existen en Inventario.
- Pequeña deuda: la pantalla de configuración tiene ahora tres tipos de control (select, porcentaje, interruptor) sin un registro de controles; se asume hasta que haya más tipos.
