# DDR-habilitar-idiomas-es-en-pt-selector-de-idioma: Selector de idioma Spa / En / Pr

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-idiomas-es-en-pt
**Fecha:** 2026-11-03

## Contexto
Hoy el header muestra una bandera (`header.component.html:18-36`) y tres opciones English / Spanish / German; solo traduce el menú lateral. El requerimiento pide un combobox en el menú superior derecho con las etiquetas **Spa**, **En**, **Pr** en lugar de banderas, y que el idioma también sea elegible en la landing.

## Pantallas/flujos afectados
1. **Header del panel** (`layout/header`): reemplaza el selector de banderas.
2. **Landing** (`features/landing`): selector en la barra superior, a la derecha, junto a los CTA.
3. **Autenticación** (login, signup, forgot, reset, `auth-layout`): selector compacto arriba a la derecha, para que una persona sin sesión pueda cambiar de idioma.
4. Todas las demás pantallas: cambian solo sus textos (sin cambios de diseño).

## Componentes/patrones elegidos
- Un único componente compartido `app-language-selector` (en `shared/components`), reutilizado en las tres ubicaciones, para que el comportamiento y la accesibilidad sean idénticos.
- Patrón visual: el `ngbDropdown` ya usado en el header (consistencia con el menú de usuario, mismas clases `header-dropdown`, `lang-dropdown-list`). Sin banderas ni imágenes.
- **Botón cerrado**: texto corto del idioma activo en `Spa`, `En` o `Pr` (con icono de globo `globe` de angular-feather a la izquierda, que ya está disponible con `allIcons`), `aria-label` traducido «Idioma».
- **Lista abierta**: tres opciones `Spa · Español`, `En · English`, `Pr · Português` (cada nombre en su propio idioma, para que se reconozca aunque la interfaz esté en otro idioma). La opción activa lleva la clase `active` y `aria-current="true"`.
- Variante de la landing: el mismo componente con el estilo de los enlaces de la barra (`landing-header.scss`), sin sombras nuevas; tokens de `design-system.md` sección 2.
- Tema oscuro: se hereda de los tokens existentes; el contraste del botón y de la opción activa debe cumplir los mínimos de `design-system.md` sección 7.

## Alternativas consideradas
- **`<select>` nativo.** Es el combobox más literal y accesible por defecto, pero rompe la apariencia del header (el resto usa `ngbDropdown`) y no se puede estilizar bien en tema oscuro. Descartada por consistencia; el dropdown implementa `role="menu"`/foco por teclado de ng-bootstrap.
- **Mantener banderas y agregar texto.** El requerimiento pide quitarlas (una bandera no representa un idioma: pt ≠ Portugal únicamente, en ≠ EE. UU.). Descartada.
- **Etiquetas ISO (ES/EN/PT).** Más estándar, pero el requerimiento fija Spa / En / Pr. Se respetan las etiquetas pedidas; el código ISO queda solo en la URL.

## Comportamiento por privilegio/estado
- Disponible para todos, con o sin sesión; no depende de permisos ni de módulos habilitados.
- **Cambiar de idioma**: la interfaz y la URL cambian al instante sin recargar la página ni perder el estado de la ruta actual (misma pantalla, mismos parámetros y query), y la elección se guarda en el navegador.
- **Cargando**: si el catálogo del idioma aún no está cargado, la interfaz conserva el idioma anterior hasta que llegue el nuevo (sin mostrar claves).
- **Error al cargar el catálogo**: se mantiene el idioma anterior y se muestra un aviso breve traducido en el idioma previo; el selector sigue operativo.
- Formularios con cambios sin guardar: cambiar de idioma **no** navega a otra pantalla, por lo que no dispara `unsavedChangesGuard` ni borra los valores escritos.
- El frontend no es barrera de seguridad: el idioma es solo presentación; no cambia permisos, datos ni respuestas del API.

## Consecuencias
- Se elimina el alemán y las banderas (`assets/images/flags/*` dejan de usarse y se borran).
- Mensajes devueltos por el backend siguen en español hasta un seguimiento (limitación aceptada y declarada).
- Deuda visual: el selector de autenticación es una incorporación mínima; si se rediseñan las pantallas de auth, se revisa su ubicación.
- Se propone añadir a `docs/design/design-system.md` (sección 3, componentes compartidos) la entrada «Selector de idioma» y una regla: **todo texto visible usa claves de traducción** (se incluye en el mismo PR).
