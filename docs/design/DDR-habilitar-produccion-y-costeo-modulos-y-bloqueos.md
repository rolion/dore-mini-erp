# DDR-habilitar-produccion-y-costeo-modulos-y-bloqueos: Módulos Producción y Costeo en Configuración → Módulos y en el menú

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-produccion-y-costeo
**Fecha:** 2026-10-30

## Contexto
Se amplía la pantalla existente (`DDR-habilitar-modulos-por-empresa-pantalla-modulos`): dos módulos nuevos, una dependencia que no es módulo (capacidad de valoración), la fecha de adopción de Costeo y bloqueos de desactivación explicados con cómo resolverlos.

## Pantallas/flujos afectados
1. **`/settings/modules`** (lista) y su **diálogo** de habilitar/deshabilitar.
2. **Menú lateral**: grupos «Producción» (Recetas, Elaboraciones, Envasados, Configuración) y «Costeo» (Configuración, Costos por lote, Análisis), visibles solo con el módulo habilitado.
3. **Pantallas destino**: `production/recipes|batches|packaging`, `costing/batches|analysis` como placeholders «Próximamente» (las funciones llegan en sus historias); `production/settings` y `costing/settings` con la pantalla de configuración existente (sin ajustes, con historial).

## Componentes/patrones elegidos
- **Lista de módulos** (plantilla Lista simple de PB-MOD-001, tabla Bootstrap): se mantienen las columnas. En «Requiere» se listan módulos y, tras ellos, las **capacidades** con la etiqueta «(capacidad)» p. ej. «Valoración de Inventario (capacidad)»; no disponible → `text-danger`. Bajo el nombre, si no se puede habilitar: «Requiere habilitar primero: …» (módulos) y «Falta la capacidad: Valoración de Inventario. Inventario aún no la ofrece.» (`text-danger`). Botón «Habilitar» `disabled` con `title`/`aria-label` con el motivo.
- **Costeo habilitado**: bajo el nombre `<small class="text-muted">Adopción: <fecha></small>` y, si la capacidad dejó de estar disponible, `<small class="text-danger">Valoración de Inventario no disponible: no se muestran costos.</small>`.
- **Deshabilitar bloqueado**: el botón queda `disabled` y bajo el nombre aparece una lista `small.text-danger` «No se puede deshabilitar: lo requieren Costeo.» y, por cada bloqueo de datos, «<mensaje>. <Cómo resolverlo>» (p. ej. «3 órdenes de producción abiertas. Ciérralas o cancélalas en Producción › Elaboraciones.»). Si el servidor responde 409 al confirmar, el mismo texto se muestra en el diálogo.
- **Diálogo** (mismo `NgbActiveModal`): se agregan filas condicionales. Habilitar Costeo: «Fecha de adopción: hoy (<fecha>)» y aviso «No se recalculan lotes anteriores; se valoran las existencias actuales.». Deshabilitar: se reemplaza el aviso genérico de PB-MOD-004 por «Tus datos e historial se conservan; los otros módulos no cambian.» para módulos que no tienen bloqueos.
- **Menú** (`routes.json`, patrón de grupos con `module`): iconos feather `tool` (Producción) y `dollar-sign` (Costeo), ubicados tras Inventario y antes de Configuración; textos i18n `MENUITEMS.PRODUCTION.*` y `MENUITEMS.COSTING.*` en es/en/de.
- **Placeholders**: `ComingSoonComponent` con `data.title` por pantalla (patrón vigente). **Configuración**: plantilla «Formulario de configuración con pestañas» (`module-settings`) reutilizada con `settingsModule`.

## Alternativas consideradas
- **Tarjetas de capacidad aparte**: más claridad visual pero se rompe la comparación en una sola tabla. Descartada.
- **Ocultar Costeo hasta que exista valoración**: el admin no sabría por qué no puede habilitarlo; se prefiere mostrarlo bloqueado con motivo.
- **Diálogo de desactivación con confirmación doble**: innecesario; si hay bloqueos no se puede confirmar y si no los hay no hay pérdida de datos.

## Comportamiento por privilegio/estado
- Estados: cargando, error con «Reintentar», éxito con toast «Módulo habilitado/deshabilitado», conflicto 409 en el diálogo con los nombres/mensajes del servidor.
- Privilegio: solo admin de empresa activa. **El backend es la barrera**: 409 por dependencias, capacidades y bloqueos; 403 `module_disabled` en las vistas de módulos deshabilitados. El menú y `moduleGuard` ocultan por comodidad.
- Accesibilidad: `title`/`aria-label` en botones deshabilitados, texto de motivo visible (no solo tooltip), contraste de `text-danger` ya usado.

## Consecuencias
Sin patrón nuevo reutilizable: no cambia `design-system.md` salvo una línea en §6 (grupos de menú Producción y Costeo). Deuda: las pantallas destino son placeholders hasta sus historias; la tabla acumula texto en la columna del nombre (se acepta por ser ≤10 filas).
