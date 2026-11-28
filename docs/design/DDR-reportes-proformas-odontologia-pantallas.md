# DDR-reportes-proformas-odontologia-pantallas: Reportes de proformas y doctor en el formulario

**Estado:** Propuesto
**Task relacionado:** TASK-reportes-proformas-odontologia
**Fecha:** 2026-11-28

## Contexto
Odontología necesita ver qué proformas faltan por cobrar y cuáles ya se pagaron, con exportación. Ya existe la pantalla de reporte compartida de ventas y compras (`DDR-reporte-ingresos-por-venta-pantalla`, componente `shared/components/document-report`).

## Pantallas/flujos afectados
1. **Menú Odontología**: dos entradas nuevas al final del submenú: «Proformas por cobrar» y «Proformas pagadas» (visibles solo con los módulos `dentistry` y `receivables` habilitados).
2. **Reporte «Proformas por cobrar»** (`/pocketbiz/dentistry/reports/receivable`) y **«Proformas pagadas»** (`/pocketbiz/dentistry/reports/paid`): plantilla *reporte* del sistema de diseño.
3. **Formulario de proforma** (`dental-proforma-form`): campo «Doctor» opcional; **detalle de proforma**: muestra el doctor.

## Componentes/patrones elegidos
- Reporte: se reutiliza `app-document-report` con dos tipos nuevos (`dental-receivable`, `dental-paid`) en `DOCUMENT_REPORT_CONFIG`. Diferencias respecto a ventas/compras, parametrizadas por configuración y no con otra pantalla:
  - Filtros: **fecha inicio y fecha fin** solamente (sin período fiscal; la configuración lo oculta).
  - Columnas: **Proforma** (número, enlace al detalle de la proforma), **Paciente**, **Doctor**, **Monto** (alineado a la derecha, formato `money`). Sin columna Saldo: en «por cobrar» Monto es el saldo y en «pagadas» el total cobrado; la cabecera de Monto lo dice («Saldo por cobrar» / «Total cobrado»).
  - Pie de totales: cantidad de proformas y suma de Monto.
  - Botones «Exportar PDF» y «Exportar Excel» con los filtros activos, estados cargando/vacío/error como en el reporte de ventas.
  - «Cliente» en la petición = **Paciente** en la interfaz (el sistema de Odontología ya usa «Paciente»; `docs/design/design-system.md` §3 y `TASK-simplificar-flujo-proforma-cobro` punto 5).
- Formulario: `ng-select`/`select` de profesionales con el patrón de `encounter-list` (`personnel.list('professionals')`), opción vacía «Sin doctor», dentro de la tarjeta de datos generales junto a la fecha. Reactive Forms.
- Detalle: línea «Doctor: <nombre>» (o «—») entre los datos de cabecera.

## Alternativas consideradas
- Pantalla propia por reporte: descartada (duplica la pantalla, filtros y exportación ya probados).
- Agrupar los reportes bajo un submenú «Reportes» anidado: descartada; ventas y compras listan los reportes planos en su módulo, se mantiene la consistencia.
- Doctor obligatorio: descartado; rompería la creación actual y las pruebas, y el usuario no lo pidió.

## Comportamiento por privilegio/estado
- Estados: cargando (indicador), vacío («No hay proformas …» con el rango activo), error (mensaje de la API), éxito (tabla + totales). Rango inválido (inicio > fin) muestra el error de validación del servidor.
- El menú oculta las entradas si falta el módulo `dentistry` o `receivables`; **la barrera real es el backend**: los endpoints exigen ambos módulos y los mismos permisos que la lista de proformas, y filtran por `company_id`.
- Móvil (390 px): la tabla usa el mismo patrón responsive que los reportes de ventas.

## Consecuencias
Pantalla de reporte con configuración más rica (columna Doctor opcional, filtro de período opcional). Las proformas ya presentadas quedan con Doctor «—» (deuda aceptada por el usuario). Sin cambios en `design-system.md`.
