# DDR-asientos-manuales-navegacion-contable-pantallas: Navegación contable y pantallas de Movimientos

**Estado:** Propuesto
**Task relacionado:** TASK-asientos-manuales-navegacion-contable
**Fecha:** 2026-11-17

## Contexto
Contabilidad tiene hoy tres ítems (Cuentas y Métodos de pago, Entradas, Regularizar) y una pantalla de configuración con siete pestañas. CONT-11 pide cuatro submenús y las pantallas para registrar y consultar asientos de partida doble (motor CONT-02). Decisiones de la persona: las pantallas existentes se conservan sin submenú propio; Saldos es «Próximamente»; Clasificaciones = las seis contables.

## Pantallas/flujos afectados
1. **Menú Contabilidad** (`routes.json`): `Cuentas` → `/pocketbiz/accounting/accounts`; `Movimientos` → `/pocketbiz/accounting/journal`; `Saldos` → `/pocketbiz/accounting/balances`; `Configuración` → `/pocketbiz/accounting/settings`. Siguen `adminOnly` y `module: accounting`. Se retiran del menú «Cuentas y Métodos de pago», «Entradas» y «Regularizar», cuyas rutas siguen vivas.
2. **Cuentas** (`/accounting/accounts`): hospeda `app-accounts-tab` (mismas acciones que hoy) con breadcrumb y `card`, sin pestañas.
3. **Configuración** (`/accounting/settings`): pestañas **Clasificaciones** (`app-account-classes-tab`) y **Períodos fiscales** (`app-periods-tab`) según «Configuración con listados en pestañas y diálogo». Bajo las pestañas, un bloque `small.text-muted` «Otras configuraciones» con enlaces a Métodos de pago, Egresos, Corte y cobertura, Entradas y Regularizar (rutas conservadas; los tres primeros siguen siendo pestañas de una pantalla heredada `/accounting/settings/legacy` — ver Alternativas). Sin lógica nueva.
4. **Movimientos** (`/accounting/journal`): plantilla «Lista de solo lectura con filtros». Filtros en la URL: fecha desde/hasta, cuenta, origen (Todos / Manual / Automático) y «Limpiar filtros». Columnas: fecha contable (`dd/MM/yyyy`), descripción, origen (badge «Manual» azul / «Automático» gris), total (`money`, alineado a la derecha), moneda, usuario. Botón primario «Nuevo asiento». Paginación del servidor con orden fijo; filtros y página se conservan al volver desde el detalle (servicio en memoria, como `StockFiltersState`).
5. **Nuevo asiento** (`/accounting/journal/new`): plantilla «Formulario con líneas» en su **variante de un solo paso con totales calculados** (no hay paso de resumen: la reversión corrige). Cabecera: fecha contable (obligatoria) y descripción (obligatoria, contador 200). Tabla de líneas Cuenta (`ng-select` solo cuentas activas, con código y moneda) / Debe / Haber (inputs numéricos de 2 decimales; escribir en uno vacía el otro) / «Quitar»; empieza con dos filas y «+ Agregar línea»; no se puede quitar por debajo de dos. Bajo la tabla, **Total Debe, Total Haber y Diferencia** de solo lectura (aritmética entera como `purchase-form`); la Diferencia usa `text-success` con «Cuadra» si es 0 y `text-danger` si no. «Confirmar asiento» (`btn-primary`) se deshabilita mientras la Diferencia ≠ 0, falte fecha/descripción, una línea sin cuenta/importe o haya menos de dos cuentas distintas, y muestra «Registrando…» al enviar. Errores del servidor junto al campo/línea (`small.text-danger`, fila `table-warning`) sin borrar lo escrito. «Cancelar» con `unsavedChangesGuard`.
6. **Detalle** (`/accounting/journal/:id`): plantilla Detalle: `dl` (fecha contable, descripción, origen, moneda, período, usuario, creado), tabla de líneas (código y nombre de cuenta, Debe, Haber, nota) con fila de totales, y bloque **Reversión** (`h5` + `dl`) cuando exista: enlace al asiento vinculado en ambos sentidos (revierte a / revertido por), motivo, fecha y usuario. Un asiento automático muestra su origen con enlace solo si `origin.available`; si no, texto «Origen: <tipo>». Sin botones de editar ni borrar. «Revertir asiento» (`btn-warning`) solo si el servidor indica `can_reverse`; si no se puede, explicación en `small.text-muted`.
7. **Diálogo de reversión** según «Diálogo de acción irreversible con motivo»: `NgbModal` estático con tabla de lo que se invierte, `alert alert-info` (efecto: crea un asiento contrario; el original no cambia), fecha (por defecto hoy) y motivo obligatorio (`textarea`, `maxlength` 200); `btn-danger` «Revertir» deshabilitado hasta tener fecha y motivo; errores (período cerrado, fecha fuera de período) dentro del diálogo sin perder lo escrito. Al terminar, el detalle se recarga con `alert alert-success`.
8. **Saldos** (`/accounting/balances`): pantalla «Próximamente» ya usada por Compras/Inventario (`alert alert-info` tenue) con breadcrumb.

## Componentes/patrones elegidos
Todo sale de `design-system.md` §3 y §5 (lista de solo lectura con filtros, formulario con totales, detalle, diálogo con motivo, configuración con pestañas, «Próximamente»). Alerta informativa en el estilo tenue de §5 (`bg-info-subtle text-info-emphasis`). Enlaces según `styles/_entry-links.scss`. Sin componentes nuevos de Oreva. Se propone documentar en §6 el nuevo submenú de Contabilidad (reemplaza las tres viñetas de Contabilidad) en el mismo PR.

## Alternativas consideradas
- **Configuración con las siete pestañas actuales**: contradice «Configuración contiene Clasificaciones y Períodos fiscales» y la decisión de la persona.
- **Retirar Métodos de pago/Egresos/Corte ya**: pierde la capacidad de mapear métodos de pago hasta CONT-12; descartado. Se conserva una pantalla heredada (`/accounting/settings/legacy`, mismas pestañas hoy: Métodos de pago, Egresos, Corte y cobertura, Clasificaciones de ingreso/egreso) alcanzable por enlace; el esfuerzo es solo de reorganizar rutas.
- **Paso de resumen antes de confirmar**: añade un clic sin evitar el error de fondo (la reversión existe); se usa un solo paso con totales visibles.

## Comportamiento por privilegio/estado
- Solo administradores de la empresa con el módulo habilitado ven el menú (`adminOnly`, `module: accounting`). **El backend aplica el mismo permiso** (`required_modules` y `CompanyModulePermission`) y el aislamiento por `company_id`; ocultar botones no sustituye la validación.
- Estados: cargando (spinner/«Cargando…»), vacío («Aún no hay asientos» con acción «Nuevo asiento»), error de servidor (`alert-danger` con «Reintentar»), éxito (`alert-success`). Lista vacía por filtro: «Sin resultados con estos filtros» y «Limpiar filtros».
- Cuenta sin código/clasificación o inactiva: no se ofrece en el selector; si el servidor la rechaza, el mensaje queda en la línea.
- Período cerrado o sin período para la fecha: error del servidor junto a la fecha.
- Un asiento automático nunca muestra edición; el servidor no ofrece ninguna ruta de edición.

## Consecuencias
- Deuda visual aceptada: la pantalla heredada de configuración mantiene el aspecto actual y se retirará con CONT-12; el selector de cuentas muestra todas las activas sin buscador avanzado.
- Entradas (libro anterior) queda fuera del menú pero accesible desde enlaces; se retira en CONT-13.
