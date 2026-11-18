# DDR-configurar-seis-clasificaciones-contables-pestana-de-configuracion: Habilitar clasificaciones contables en Configuración

**Estado:** Propuesto
**Task relacionado:** TASK-configurar-seis-clasificaciones-contables
**Fecha:** 2026-11-16

## Contexto
La persona administradora decide cuáles de las seis clasificaciones contables usa su empresa. No hay alta, edición ni borrado. Las cuentas se clasifican con una de las habilitadas.

## Pantallas/flujos afectados
1. **Configuración de Contabilidad → pestaña nueva «Clasificaciones contables»** (`accounting-settings`): lista de seis filas fijas con interruptor habilitar/deshabilitar.
2. **Diálogo de cuenta (`account-dialog`)**: selector opcional «Clasificación contable» con solo las habilitadas; si la cuenta ya tiene una deshabilitada, se muestra seleccionada con la etiqueta «(deshabilitada)» y no se ofrece a otras cuentas.

## Componentes/patrones elegidos
- Plantilla «Configuración con listados en pestañas» (`docs/design/design-system.md` sección 5; referencia `features/inventory/pages/inventory-configuration`) y la estructura de `classifications-tab` (encabezado, tabla responsive con `data-label`, badges `badge-outline col-green/col-red`). Sin componentes Oreva nuevos.
- Acción: botón de texto «Habilitar»/«Deshabilitar» por fila, con `aria-label` que incluye el nombre; sin diálogo de confirmación porque la acción es reversible y no altera datos. Una línea de ayuda aclara «Deshabilitar no modifica cuentas existentes ni saldos».
- La pestaña CONT-01 conserva su nombre; la nueva se llama «Clasificaciones contables» y el texto de ayuda de ambas aclara su diferencia (movimiento frente a cuenta).

## Alternativas consideradas
- **Reemplazar la pestaña «Clasificaciones» existente:** rompe egresos ya integrados; se pospone a CONT-11.
- **Interruptores en línea (toggle):** el sistema de diseño usa botones con texto para acciones de estado; se mantiene la consistencia.

## Comportamiento por privilegio/estado
- Estados: cargando, error con «Reintentar», éxito (la fila cambia de badge y se anuncia con `aria-live`). Sin vacío: siempre hay seis.
- Solo administradores de la empresa ven y usan la pestaña. **El backend aplica permiso, aislamiento por empresa y rechazo de clasificaciones deshabilitadas; el frontend no es la barrera.**
- Todos los textos con `translate` en es/en/pt.

## Consecuencias
Dos pestañas con nombre parecido hasta CONT-11 (deuda visual aceptada, mitigada con texto de ayuda). Sin cambios en `design-system.md`.
