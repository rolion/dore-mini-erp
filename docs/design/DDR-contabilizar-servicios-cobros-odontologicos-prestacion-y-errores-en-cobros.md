# DDR-contabilizar-servicios-cobros-odontologicos-prestacion-y-errores-en-cobros: Marcar tratamientos como prestados y rechazos contables accionables

**Estado:** Propuesto
**Task relacionado:** TASK-contabilizar-servicios-cobros-odontologicos
**Fecha:** 2026-11-17

## Contexto
La persona que cobra necesita indicar qué tratamientos ya se prestaron (reconocen ingreso) y entender por qué una acción es rechazada por Contabilidad. La pantalla existe (detalle del compromiso, `features/receivables/pages/commitment-detail`); no hay pantallas nuevas.

## Pantallas/flujos afectados
- **Detalle del compromiso (Cobros):** columna «Prestación» en la tabla de tratamientos y acción por fila.
- **Diálogo de cobro (`shared/components/payment-dialog`) y panel de cobro (`collection-panel`)** en proforma y ficha del paciente: mostrar los rechazos contables 409.
- **Resumen del detalle:** nuevo total «Reconocido» junto a Aceptado/Cobrado/Saldo.

## Componentes/patrones elegidos
- Plantilla «Detalle con selección de líneas y registro de decisión» (`design-system.md` §5) y componentes compartidos: `app-status-badge` para el estado «Prestado el dd/MM/aaaa» / «Sin prestar», `money`, diálogo de confirmación como los demás diálogos compartidos.
- **Acción por fila** «Marcar como prestado» (botón secundario, solo en líneas aceptadas sin prestar y proforma vigente). Abre un diálogo de confirmación con: nombre del tratamiento, importe, **fecha de prestación** (por defecto hoy, no futura) y texto claro «No se puede deshacer. Reconoce el ingreso por servicios y aplica los anticipos cobrados». Al éxito: la fila pasa a «Prestado» y se anuncia con `role="status"`; el foco vuelve al botón o a la fila.
- **Errores 409:** alerta tenue (estilo ya usado por VEN-01, contraste AA, enlace heredando el color del texto) con el `detail`; para `posting_configuration_missing` lista los `issues` y enlaza a la configuración de Ventas/Cobros → pestaña «Asientos automáticos». El componente de alerta de VEN-01 se **extrae a `shared/components`** y lo reutilizan Ventas y Cobros (refactor sin cambio visual).
- Texto nuevo siempre con claves `translate` en es/en/pt.

## Alternativas consideradas
- **Casilla por fila + botón global «Guardar prestados»:** permite equivocarse en lote y complica el error parcial; descartado frente a una acción confirmada por fila (irreversible).
- **Deshabilitar de antemano según configuración/cobertura:** acopla el frontend a reglas contables; el servidor decide y la alerta explica.
- **Pantalla nueva «Servicios prestados»:** fuera de alcance; el detalle del compromiso ya tiene el contexto (cliente, tratamientos, cobros).

## Comportamiento por privilegio/estado
Mismo permiso que cobrar (módulo `receivables` + fuente; acceso clínico en Odontología). Proforma no vigente, línea rechazada/sin decidir o ya prestada: sin botón. El frontend no es la barrera: el backend valida estado, permisos, fecha y cobertura. Estados: cargando (botón deshabilitado con `aria-busy`), error 409/validación (alerta en el diálogo, sin cerrarlo), éxito.

## Consecuencias
Sin patrón nuevo salvo el componente de alerta compartido (se documentará en `design-system.md` §3). Revisión visual en escritorio y 375 px, temas claro y oscuro, pendiente para `delivery-publish`.
