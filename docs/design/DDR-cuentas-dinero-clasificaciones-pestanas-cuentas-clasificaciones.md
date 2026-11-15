# DDR-cuentas-dinero-clasificaciones-pestanas-cuentas-clasificaciones: Tipo de cuenta y pestaña «Clasificaciones»

**Estado:** Propuesto
**Task relacionado:** TASK-cuentas-dinero-clasificaciones
**Fecha:** 2026-11-15

## Contexto
La página Contabilidad → Configuración (`features/accounting/pages/accounting-settings`) tiene pestañas «Cuentas» y «Métodos de pago». Hay que mostrar el tipo de cuenta y administrar clasificaciones de ingreso y egreso.

## Pantallas/flujos afectados
- **Pestaña Cuentas:** columna «Tipo» (Caja/Banco/Billetera o «Sin tipo»); el diálogo de cuenta añade un selector de tipo (obligatorio al crear).
- **Pestaña nueva «Clasificaciones»:** lista con filtros de dirección (Todas/Ingresos/Egresos) y estado (por defecto activas), alta/edición en diálogo (nombre y dirección; la dirección no se edita), activar/desactivar.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (`docs/design/design-system.md:141`, referencia `inventory-configuration`), reutilizando la estructura de `AccountsTabComponent`/`AccountDialogComponent`; badges de estado de la sección 3; selector nativo `form-select` como en el diálogo de cuenta actual. Sin componentes nuevos de la plantilla Oreva.

## Alternativas consideradas
- Página separada para clasificaciones: más navegación sin beneficio; se prefiere la pestaña.
- Segmentar por dirección en dos pestañas: duplica estructura; un filtro basta.

## Comportamiento por privilegio/estado
Estados cargando, vacío («Aún no hay clasificaciones»), error con reintento y éxito por toast. Desactivar pide confirmación breve; el bloqueo 409 de cuentas conserva su mensaje actual. Solo administradores de empresa acceden; **el backend aplica permisos y aislamiento por empresa**, el frontend no es la barrera.

## Consecuencias
Cuentas antiguas «Sin tipo» quedan visibles hasta completarse. Textos en es/en/pt con las mismas claves. No hay deuda visual nueva.
