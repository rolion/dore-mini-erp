# DDR-menu-por-tipo-de-empresa-selector-y-menu: Selector de tipo en el registro y menú ordenado por tipo

**Estado:** Propuesto
**Task relacionado:** TASK-menu-por-tipo-de-empresa
**Fecha:** 2026-11-26

## Contexto
La persona debe elegir el tipo de negocio al registrarse y ver un menú lateral acorde. No hay pantallas nuevas.

## Pantallas/flujos afectados
- `/pocketbiz/signup`: un campo nuevo, obligatorio.
- Menú lateral (sidebar): orden y ubicación de ítems según el tipo.

## Componentes/patrones elegidos
- **Signup** (plantilla «Autenticación», `design-system.md:213`): un `form-select` nativo con `label` «Tipo de empresa» y asterisco de obligatorio, entre «Nombre de la empresa» y «Nombre». Opciones, con una línea de ayuda `small.form-text.text-muted` bajo el campo que cambia según la opción elegida: Compraventa («Compras y ventas de productos, con inventario»), Servicios («Cotizaciones, cobros y agenda»), Odontología («Servicios de atención odontológica»). Sin opción preseleccionada: el primer valor es «Selecciona un tipo» y valida como obligatorio. Se usa `select` nativo y no `ng-select` porque son tres opciones sin búsqueda, como los demás `form-select` del sistema.
- **Texto de apoyo** (una frase bajo el campo): «Define los módulos con los que empiezas. Podrás activar más después en Ajustes.» Evita que la persona crea que está eligiendo una limitación.
- **Menú:** misma presentación del sidebar actual; solo cambia el orden. En el tipo Odontología, «Presupuestos» aparece como segundo subítem de «Odontología», después de «Pacientes» (que sigue siendo la entrada principal), y su ítem de primer nivel «Cotizaciones» deja de mostrarse.
- Orden por tipo (Ajustes siempre al final; lo no listado se agrega antes de Ajustes):
  - Compraventa: Inicio, Catálogo, Clientes, Ventas, Compras, Inventario, Contabilidad, Gastos, Reportes.
  - Servicios: Inicio, Catálogo, Clientes, Cotizaciones, Cobros, Agenda, Personal, Contabilidad, Gastos, Reportes.
  - Odontología: Inicio, Catálogo, Clientes, Odontología, Cobros, Agenda, Personal, Contabilidad, Gastos, Reportes.
  - General (empresas existentes y tipo desconocido): el orden actual.

## Alternativas consideradas
- **Tarjetas de selección con icono** (una por tipo): más vistosas, pero no existe el componente en el sistema y el formulario es angosto. Descartada por consistencia y esfuerzo.
- **Pregunta en un paso aparte tras el alta:** añade un paso y deja la empresa sin tipo un momento. Descartada.
- **Ítem «Presupuestos» de primer nivel en odontología:** repite «Cotizaciones» con otro nombre. Descartada por la decisión del usuario de mostrarlo dentro de Odontología.

## Comportamiento por privilegio/estado
- El selector es obligatorio: sin valor se muestra «Selecciona el tipo de empresa» y no se envía. Un error del servidor sobre `company_type` se muestra bajo el campo, como los demás.
- Un módulo apagado oculta su ítem aunque el tipo lo ubique; el menú nunca muestra lo que la empresa no tiene habilitado. «Presupuestos» desaparece de Odontología si el módulo Cotizaciones se desactiva.
- **El backend es la barrera real:** valida que el tipo sea uno de los tres públicos, y el acceso a cada módulo sigue controlado por el permiso de módulo de la API. El menú es solo presentación.

## Consecuencias
- Las claves de traducción nuevas existen en es/en/pt.
- El menú de empresas existentes no cambia.
- Se actualiza `docs/design/design-system.md` (sección 6, menú dinámico) con la regla de orden por tipo.
