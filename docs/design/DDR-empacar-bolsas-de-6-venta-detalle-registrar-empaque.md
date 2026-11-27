# DDR-empacar-bolsas-de-6-venta-detalle-registrar-empaque: Registrar empaque en el detalle de la orden

**Estado:** Propuesto
**Task relacionado:** TASK-empacar-bolsas-de-6-venta-detalle
**Fecha:** 2026-11-27

## Contexto
La orden Listo para empacar (PROD-005) no tiene salida hacia producto de venta. El operario necesita registrar tandas de packs de 6 y ver su historial y el saldo a granel.

## Pantallas/flujos afectados
- Detalle de orden (`features/production/pages/order-detail`): acción «Registrar empaque» (solo `ready_to_pack`), sección «Empaques» con saldo a granel e historial.
- Lista de órdenes: sin cambios.

## Componentes/patrones elegidos
- Plantilla **Detalle** de `docs/design/design-system.md` (sección 5): acción principal `btn-primary` bajo los datos; sección `h5` con historial en tabla Bootstrap apilada, vacío explicado («Aún no hay empaques»). Misma estructura que la sección «Liberación» del DDR de PROD-005.
- «Registrar empaque» abre un diálogo `NgbModal` (`backdrop: 'static'`) con Reactive Forms: Producto pack y Producto bolsa (`ng-select` sobre productos que controlan stock, ya usados en la app), «Cantidad de packs» (entero ≥ 1). Resumen en vivo de solo lectura: «Se descontarán N × 6 cuñapés del lote L-… y N bolsas; ingresarán N packs», con el saldo a granel disponible. Pie: «Registrar» (primario) y «Cancelar» (`btn-light`).
- Sin componentes compartidos nuevos ni desviaciones del sistema de diseño.

## Alternativas consideradas
- Página aparte `order-pack`: más consistente con `order-refrigerate`, pero el formulario tiene 3 campos; el diálogo evita navegar. Elegido el diálogo.
- Configurar pack y bolsa en Ajustes o en la receta: descartado por el usuario (se eligen en cada empaque).

## Comportamiento por privilegio/estado
- El botón solo aparece en `ready_to_pack`; si el saldo a granel es menor que 6 se deshabilita con `small.text-muted` («Quedan N cuñapés a granel: no alcanzan para un pack»).
- Estados: cargando (botón deshabilitado, «Registrando…»), error de campo bajo el campo, **faltantes** (409 `insufficient_stock`) como lista «Falta X: necesitas N, hay M» dentro del diálogo, éxito (cierra y recarga detalle con «Guardado ✓»).
- El doble clic reutiliza el mismo `request_id` del diálogo abierto; un nuevo diálogo genera uno nuevo.
- El frontend no es la barrera: el backend valida estado, lote liberado, saldos, productos y módulo habilitado (403/409/400).

## Consecuencias
Sin deuda visual nueva. El historial no pagina (se espera un número bajo de tandas por orden); si crece, se pagina después.
