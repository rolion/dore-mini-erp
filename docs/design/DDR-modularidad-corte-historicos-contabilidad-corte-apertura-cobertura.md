# DDR-modularidad-corte-historicos-contabilidad-corte-apertura-cobertura: Pestaña «Corte y cobertura», saldo de apertura y avisos de cobertura

**Estado:** Propuesto
**Task relacionado:** TASK-modularidad-corte-historicos-contabilidad
**Fecha:** 2026-11-15

## Contexto
Contabilidad › Configuración tiene pestañas Cuentas, Métodos de pago y Clasificaciones. Hay que mostrar y administrar la fecha de corte, el saldo de apertura por cuenta, los periodos sin cobertura y el motivo de un bloqueo al deshabilitar.

## Pantallas/flujos afectados
- **Pestaña nueva «Corte y cobertura»:** fecha de corte (editable con confirmación mientras no haya movimientos; luego solo lectura con una nota «No se puede cambiar: ya hay movimientos»), fecha de habilitación, lista de periodos sin cobertura (desde–hasta) y una nota fija: «Lo registrado antes del corte o durante una desactivación no se contabiliza automáticamente».
- **Cuentas:** el diálogo añade «Saldo de apertura» (decimal ≥ 0, a la fecha de corte); se deshabilita con el motivo cuando la cuenta ya tiene movimientos; la tabla muestra la columna «Apertura».
- **Libro de entradas:** aviso (`alert-warning`) sobre la tabla cuando haya periodos sin cobertura o el libro empiece después del corte, con enlace a «Corte y cobertura».
- **Módulos (Configuración › Módulos):** al deshabilitar Contabilidad, un 409 `disable_blocked` se muestra con el texto del servidor y los bloqueadores.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (`docs/design/design-system.md:141`; referencia `inventory-configuration`), reutilizando `AccountsTabComponent`/`AccountDialogComponent`, `alert-warning` de `features/accounting/components/_alert-warning.scss`, badges y tabla apilada. Fecha con `input type="date"` y confirmación en `NgbModal`. Sin componentes nuevos de la plantilla Oreva.

## Alternativas consideradas
- Mover el corte a la pantalla de módulos: mezcla configuración contable con activación; se mantiene en Contabilidad.
- Editar la apertura en una tabla aparte: más pantallas sin beneficio; se edita en el diálogo de la cuenta.

## Comportamiento por privilegio/estado
Cargando, vacío («Sin periodos sin cobertura»), error con reintento y éxito por aviso. Solo administradores de empresa; **el backend aplica permisos, aislamiento por empresa y las reglas de bloqueo (409 `cutoff_locked`, `account_has_entries`, `disable_blocked`)**; el frontend no es la barrera.

## Consecuencias
Cuentas existentes muestran apertura 0,00. Textos en es/en/pt con las mismas claves. Sin deuda visual nueva.
