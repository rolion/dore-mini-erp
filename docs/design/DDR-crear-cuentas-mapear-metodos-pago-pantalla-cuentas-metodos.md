# DDR-crear-cuentas-mapear-metodos-pago-pantalla-cuentas-metodos: Pantalla «Cuentas y Métodos de pago»

**Estado:** Propuesto
**Task relacionado:** TASK-crear-cuentas-mapear-metodos-pago
**Fecha:** 2026-11-13

## Contexto
La persona administradora debe definir cuentas destino y a cuál va cada método de pago antes de habilitar Contabilidad. Hay que reutilizar el estilo PocketBiz (`docs/design/design-system.md`).

## Pantallas/flujos afectados
- Menú lateral nuevo: **Contabilidad → Configuración → Cuentas y Métodos de pago** (`/pocketbiz/accounting/settings`), ítem con `module: accounting`. El ítem del menú sigue al módulo `accounting` (oculto si está deshabilitado) y solo es visible para admin. La ruta no lleva `moduleGuard`: la configuración previa a habilitar se alcanza desde Módulos, con el enlace del 409 `incomplete_configuration`. *(Ajuste posterior: antes el ítem era visible siempre; se corrigió porque seguía apareciendo con el módulo deshabilitado.)*
- Pantalla con dos pestañas: **Cuentas** (lista + alta/edición en diálogo + activar/desactivar) y **Métodos de pago** (cinco filas fijas: método, cuenta destino en `ng-select`, estado activo, guardar por fila).
- Pantalla de Módulos (`/settings/modules`): al intentar habilitar Contabilidad con mapeo incompleto se muestra el 409 con los métodos faltantes y un enlace a esta pantalla.

## Componentes/patrones elegidos
Plantilla «Configuración con listados en pestañas y diálogo» (`features/inventory/pages/inventory-configuration`, design-system §5) con componentes compartidos §3: tabla simple Bootstrap, badges de estado (`badge-outline`), botones `btn-primary`, diálogo `NgbActiveModal` para crear/editar cuenta (nombre, moneda), diálogo de confirmación para desactivar. Sin componentes nuevos del tema.

## Alternativas consideradas
- Una sola tabla método→cuenta con alta de cuentas en línea: menos pasos pero mezcla dos conceptos; descartada.
- Dos pantallas separadas: más navegación para un ajuste de 5 filas; descartada.

## Comportamiento por privilegio/estado
- **Cargando:** esqueleto/indicador de la plantilla. **Vacío:** pestaña Cuentas sin cuentas muestra explicación y botón «Crear cuenta»; en Métodos, cada método aparece «Sin cuenta». **Error:** alerta con reintentar. **Éxito:** toast de confirmación.
- Cuenta desactivada con métodos activos asignados: el diálogo lista los métodos afectados y bloquea; ofrece ir a Métodos de pago.
- Selector de cuenta: solo cuentas activas en moneda BOB; las de otra moneda se muestran deshabilitadas con la etiqueta de moneda incompatible.
- Un usuario no admin no ve el menú ni accede a la ruta. **El frontend no es la barrera:** el backend aplica admin, empresa del usuario, cuenta ajena, moneda y desactivación segura.
- Todo texto con claves i18n es/en/pt.

## Consecuencias
Una pantalla nueva alineada con Inventario → Configuración; sin deuda visual nueva. Si más adelante hay más métodos, la lista fija pasaría a ser dinámica.
