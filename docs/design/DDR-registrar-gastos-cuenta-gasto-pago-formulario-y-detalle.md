# DDR-registrar-gastos-cuenta-gasto-pago-formulario-y-detalle: Cuentas de gasto y de pago en el formulario y el detalle de gastos

**Estado:** Propuesto
**Task relacionado:** TASK-registrar-gastos-cuenta-gasto-pago
**Fecha:** 2026-11-17

## Contexto
Registrar un gasto con Contabilidad cubriendo la fecha genera un asiento. La persona debe ver y poder cambiar las cuentas antes de confirmar, y el detalle debe mostrar qué se contabilizó. No se crean pantallas.

## Pantallas/flujos afectados
- `features/expenses/pages/expense-form` (alta y edición), `expense-detail`, y la ayuda de clasificación (`classification-hint`) que deja de aparecer en el alta.

## Componentes/patrones elegidos
Plantillas de Formulario y Detalle (`docs/design/design-system.md` §5) y la variante «Panel de cuentas por evento con vista previa Debe/Haber» (referencia `features/accounting/components/posting-config-panel`):
- Bloque «Contabilidad» en el formulario, visible solo si hay cobertura (`posting-options`): selector «Cuenta de gasto» (por defecto la de la categoría) y «Cuenta de pago» (por defecto la del método), ng-select con las elegibles; vista previa Debe/Haber con el importe.
- Si faltan cuentas por defecto: aviso accionable con enlace a la configuración (misma forma que `classification-hint`) y el guardado se deshabilita hasta elegir una cuenta o configurar.
- Sin cobertura: el bloque no aparece y el gasto se registra como hoy.
- Detalle: sección «Asiento contable» (cuentas, enlace al asiento) y badge «Contabilizado»; en edición, los campos bloqueados quedan de solo lectura con nota «Para corregir, anule el gasto y regístrelo de nuevo».
- Anular: el diálogo de acción irreversible existente; el error de período cerrado se muestra como alerta accionable.
- Texto solo con claves `es/en/pt`; tokens y badges del sistema de diseño.

## Alternativas consideradas
Cuentas dentro de un diálogo aparte (más pasos, rompe la plantilla de formulario de un paso): descartada. Mostrar siempre el bloque (confunde a quien no usa Contabilidad): descartada.

## Comportamiento por privilegio/estado
Cargando (opciones), vacío (sin cuentas elegibles → aviso), error (400 por campo, 409 de clave o período) y éxito como el resto del módulo. Backend: aislamiento por empresa, validación de cuentas, bloqueo de campos y cobertura se aplican en el servidor; el frontend no es la barrera.

## Consecuencias
Sin deuda visual nueva ni componentes compartidos nuevos; el patrón de vista previa Debe/Haber se reutiliza en Compras (COM-01).
