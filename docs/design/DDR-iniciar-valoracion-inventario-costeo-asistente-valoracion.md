# DDR-iniciar-valoracion-inventario-costeo-asistente-valoracion: Asistente de valoración inicial y consulta de valores

**Estado:** Propuesto
**Task relacionado:** TASK-iniciar-valoracion-inventario-costeo
**Fecha:** 2026-10-30

## Contexto
El admin debe asignar un valor inicial en BOB a las existencias para activar el costeo (PB-VAL-001). Es una acción única e irreversible, por lo que lleva paso de resumen.

## Pantallas/flujos afectados
- **Inventario → Configuración → «Valoración»** (enlace/pestaña visible solo si el módulo `costing` está habilitado): ruta `inventory/valuation`.
  - *Sin adopción:* asistente en la misma ruta con pasos **1 Conciliar** (cantidades por producto con desglose por almacén, solo lectura; bloqueos de stock negativo en `alert alert-warning`), **2 Valores** (tabla de líneas: producto, unidad base, cantidad conciliada, *Valor total (BOB)*, casilla «Declarar costo cero», fuente, costo unitario derivado de solo lectura o badge «Pendiente») y **3 Confirmar** (resumen `dl.row` + tabla de solo lectura; «Confirmar adopción» primario, «Volver a editar» `btn-light`).
  - *Con adopción:* detalle de solo lectura: `dl.row` (fecha de corte, usuario, método «Promedio ponderado móvil (costo de gestión)») y tabla de valores por producto con búsqueda por nombre.
- **Pantalla de módulos** (`settings/modules`): aparece la tarjeta «Costeo» sin cambios de diseño.

## Componentes/patrones elegidos
- Plantilla «Formulario con líneas y paso de resumen» (referencia `features/inventory/pages/stock-opening`) para los pasos 2-3 y «Detalle» + «Lista de solo lectura» para la consulta; tabla apilada `_inventory-table.scss`; `MoneyPipe` para BOB; badges de texto («Pendiente», «Costo cero»).
- Aviso permanente `alert alert-info`: «Costo de gestión con promedio ponderado móvil; no es una política fiscal ni contable.»
- Sin componentes fuera del sistema de diseño.

## Alternativas consideradas
- Una sola tabla sin resumen: descartada, la adopción es irreversible.
- Edición posterior de valores: descartada por el requisito de corte protegido.

## Comportamiento por privilegio/estado
- Estados: cargando, vacío («No hay existencias que valorar»; se puede confirmar), error (`alert-danger` + «Reintentar»), éxito (consulta con `alert-success`).
- Costo ausente: «Pendiente» en la fila y «Revisar resumen» deshabilitado con explicación; costo cero solo con la casilla marcada.
- Con adopción hecha no se ofrece ninguna acción de edición.
- El backend aplica todo (módulo `costing` habilitado → 403 si no; admin; bloqueos; reglas de adopción); el frontend solo oculta la entrada.

## Consecuencias
Pantalla nueva con patrones ya existentes; sin deuda visual nueva. No se modifica `design-system.md`.
