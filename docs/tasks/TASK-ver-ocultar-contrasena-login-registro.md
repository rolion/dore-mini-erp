# TASK-ver-ocultar-contrasena-login-registro: Ver/ocultar contraseña en login y registro

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-ver-ocultar-contrasena-login-registro
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-26 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-26 | INVESTIGATION → PLANNING | NEEDS_PLAN, sin diseño ni arquitectura | delivery-start |
| 2026-11-26 | PLANNING → ENGINEERING | Specification READY, plan v1 | delivery-start |

## Investigación

### Requerimiento
Al hacer login o crear una cuenta, el campo contraseña está siempre oculto. Agregar dentro del campo un icono de ojo que, al hacer click, muestre la contraseña; cuando no se muestre, el icono es un ojo tachado. Estado inicial: contraseña oculta con ojo tachado.

### Hechos encontrados
- `frontend/panel_admin/src/app/authentication/signin/signin.component.html:27` — input `type="password"` con `psl-5` (icono de llave a la izquierda, `.login-icons`).
- `frontend/panel_admin/src/app/authentication/signup/signup.component.html:91` y `:102` — «Contraseña» y «Confirmar contraseña», mismo patrón.
- `frontend/panel_admin/src/assets/scss/components/_auth.scss:219` — `.login-icons` posiciona el icono Feather absoluto (`top:37px; left:18px`); RTL en `rtl/_components-rtl.scss:114`; oscuro en `skins/_dark.scss:1035`.
- `app/app.config.ts:35` y specs de signin/signup — `FeatherModule.pick(allIcons)`: `eye` y `eye-off` disponibles.
- `docs/design/design-system.md:213` — sección Autenticación (tarjeta angosta); no define toggle de contraseña.
- `authentication/reset/reset.component.html:19,28` también tiene contraseñas, fuera del pedido.

### Hipótesis / supuestos no confirmados
- «Crear una cuenta» = signup (ambos campos de contraseña llevan el toggle, cada uno independiente). Reset queda fuera.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio frontend acotado (2 plantillas, un componente compartido pequeño, i18n), sin backend ni decisión arquitectónica.

### Diseño requerido
**NO** — no hay pantallas nuevas; es un control dentro de un campo existente.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
docs/plans/PLAN-2026-11-26-ver-ocultar-contrasena-login-registro.md (v1, COMPACTO)

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
