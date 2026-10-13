# REV-2026-10-13-perfil-usuario-menus-lateral-superior-01: Empresa/nombre largos desbordan el sidebar y la elipsis nunca se aplica

**Status:** Fixed (pendiente de verificación por delivery-review)
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-13-perfil-usuario-menus-lateral-superior.md (v1)
**Spec reference:** Edge/error cases — "nombre o empresa largos (elipsis con `title`, sin desbordar)"; DDR punto 5 (truncado por elipsis y `title`)
**Plan mode:** COMPACTO
**Suggested owner:** delivery-engineer

## Description
En `frontend/panel_admin/src/assets/scss/layouts/_sidebar.scss` (bloque nuevo `.sidebar-userpic-name, .profile-usertitle-job { overflow:hidden; padding:0 12px; text-overflow:ellipsis; white-space:nowrap }`) la elipsis no tiene efecto: el contenedor del texto (`.profile-usertitle` → `li` → `ul.list` → `ng-scroll-content`) toma el ancho intrínseco del texto `nowrap` y crece más que el sidebar (260px), de modo que el elemento nunca queda "más estrecho que su contenido" y el texto simplemente se recorta por el `overflow:hidden` del `<aside>`, sin `…`, además de dejar el contenido del scroll más ancho que el viewport.

## Expected behavior
Edge case de la Specification: nombre o empresa largos se truncan con elipsis y `title`, sin desbordar el sidebar.

## Actual behavior
Con una sesión `company.name = "Cuñapés Artesanales de la Región Andina SRL"` (43 caracteres, plausible) en `ng serve` (Chrome, 1280x800, sidebar expandido), el texto se corta en el borde derecho sin elipsis (`…`) y el ancho del contenedor excede al del sidebar.

## Evidence
Medición en el DOM (sidebar expandido, tema claro):
```
DIV.profile-usertitle-job  w=286 ov=hidden pad=12px/12px  (text-overflow: ellipsis, white-space: nowrap)
DIV.profile-usertitle      w=286
LI.sidebar-user-panel      w=286
UL.list                    w=286
NG-SCROLL-CONTENT          w=286
NG-SCROLLBAR (viewport)    w=259
ASIDE.sidebar              w=260 ov=hidden
```
scrollWidth == clientWidth == 286 en `.profile-usertitle-job` ⇒ nada que truncar; el ancho del padre (286) > sidebar (260). El header (menú de usuario) sí envuelve el texto correctamente.

Nota: el spec del sidebar no cubre este caso (jsdom/Karma no mide layout); la verificación visual manual del plan lo habría detectado.

Sugerencia (no vinculante): acotar el ancho del bloque (`max-width: 100%`/`width: 100%` o `display: block; min-width: 0` + `contain` en `.profile-usertitle`/`li.sidebar-user-panel`) para que `ng-scroll-content` no crezca con el texto, y volver a verificar visualmente con nombre y empresa largos, sidebar colapsado y tema oscuro.
