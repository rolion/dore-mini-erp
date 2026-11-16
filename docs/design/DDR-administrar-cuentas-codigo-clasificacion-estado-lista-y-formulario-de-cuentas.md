# DDR-administrar-cuentas-codigo-clasificacion-estado-lista-y-formulario-de-cuentas: Plan de cuentas en la pestaña Cuentas

**Estado:** Propuesto
**Task relacionado:** TASK-administrar-cuentas-codigo-clasificacion-estado
**Fecha:** 2026-11-16

## Contexto
La persona administra el plan de cuentas de su empresa: crea, edita y habilita o deshabilita cuentas con código, nombre y clasificación. Algunas cuentas son de dinero (Caja, Bancos) y una puede ser correctora.

## Pantallas/flujos afectados
1. **Contabilidad › Configuración › Cuentas (`accounts-tab`)**: lista con columnas Código, Nombre, Clasificación, Tipo de dinero (si lo tiene), Moneda, Apertura, Estado y Acciones; filtros por estado (los actuales) y por clasificación. Orden por código; las cuentas sin código van al final con «Sin código». Una cuenta correctora lleva la etiqueta «Correctora» junto al nombre.
2. **Diálogo de cuenta (`account-dialog`)**:
   - **Código** (obligatorio, solo números, p. ej. «111001»; la ayuda aclara que es único en la empresa y que otra empresa puede repetirlo) y **Nombre** (obligatorio).
   - **Clasificación** (obligatoria): solo las habilitadas; al editar, la actual aparece aunque esté deshabilitada. Con asientos, el campo está deshabilitado y un texto explica por qué.
   - **Cuenta de dinero** (tipo Caja/Banco/Billetera, opcional): visible solo con Activo.
   - **Cuenta correctora**: casilla, con ayuda «Su saldo normal es contrario al de su clasificación». Con asientos, deshabilitada.
   - Moneda y saldo de apertura como hoy.
3. **Deshabilitar** conserva el diálogo actual (`deactivate-dialog`): si hay métodos activos, muestra el 409 con la lista y pide reasignarlos. No hay botón de borrar.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas» y la estructura actual de `accounts-tab`/`account-dialog` (`docs/design/design-system.md` sección 5); badges `badge-outline`, tabla `inventory-table` con `data-label`, botones `btn-tbl-*`. Sin componentes Oreva nuevos.

## Alternativas consideradas
- **Pantalla nueva «Plan de cuentas» aparte:** duplica la pestaña; CONT-11 reorganiza la navegación después.
- **Mostrar el tipo de dinero siempre:** confunde en cuentas que no mueven dinero; se muestra solo con Activo.

## Comportamiento por privilegio/estado
- Estados: cargando, vacío («Aún no hay cuentas»), error con «Reintentar», éxito con aviso. Errores de campo del servidor junto al campo (código repetido, clasificación deshabilitada).
- Solo administradores de la empresa. **El backend aplica permisos, aislamiento por empresa, unicidad del código, clasificaciones habilitadas y el bloqueo por asientos; el frontend no es la barrera.**
- Textos con `translate` en es/en/pt.

## Consecuencias
Las cuentas anteriores se verán con «Sin código» y sin clasificación hasta editarlas. Sin cambios en `design-system.md`.
