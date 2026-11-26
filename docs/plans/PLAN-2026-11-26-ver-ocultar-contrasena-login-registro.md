# PLAN-2026-11-26-ver-ocultar-contrasena-login-registro (v1)

**Task:** TASK-ver-ocultar-contrasena-login-registro · **Modo:** COMPACTO · **Specification readiness:** READY
**DDRs / ADRs:** Ninguno

## Objective
Permitir ver/ocultar la contraseña con un botón-icono dentro del campo en login y registro.

# Specification
- **Expected behavior:** en login (1 campo) y registro (2 campos), cada campo de contraseña tiene a la derecha, dentro del input, un botón con icono. Inicial: contraseña oculta e icono ojo tachado (`eye-off`). Click: se muestra el texto e icono ojo (`eye`); otro click vuelve a ocultar. Cada campo es independiente.
- **Acceptance criteria:**
  - AC-01: estado inicial `type="password"` e icono `eye-off` en los 3 campos.
  - AC-02: click en el botón → `type="text"` e icono `eye`; segundo click → vuelve a `password`.
  - AC-03: el botón es `type="button"` (no envía el formulario), accesible por teclado, con `aria-label` traducido (es/en/pt) y `aria-pressed`; el valor del control no cambia.
  - AC-04: el texto del input no queda bajo el icono (padding derecho); funciona en RTL y tema oscuro.
- **Edge/error cases:** mensajes de error del campo siguen mostrándose bajo el input sin que el icono se desplace.
- **Out of scope:** `reset`, formularios de la plantilla de demostración, backend.

# Test Specification
- Unit (Karma) en specs de signin y signup: AC-01, AC-02, AC-03 (estado, alternancia, no submit, valor intacto). Spec del componente compartido. Test de i18n existente cubre claves es/en/pt.
- **E2E: NO** — flujo simple cubierto por pruebas de componente.

# Implementation Plan
- **Files affected (frontend):** nuevo `shared/components/password-toggle/` (componente standalone que recibe el `HTMLInputElement` y alterna `type`; iconos Feather `eye`/`eye-off`); `signin.component.html/.ts`, `signup.component.html/.ts` (import); `assets/scss/components/_auth.scss` (+ RTL y dark); `assets/i18n/{es,en,pt}.json` (claves `AUTH.COMMON.MOSTRAR_CONTRASENA`/`OCULTAR_CONTRASENA`); `docs/design/design-system.md` (nota en «Autenticación»); specs.
- **Steps:** 1) componente + spec (AC-01..03); 2) estilos con padding derecho y posición (AC-04); 3) integrar en los 3 campos; 4) i18n y `npm run i18n:check`; 5) actualizar design-system; 6) lint y test.
- **Risks / New dependencies:** ninguna dependencia nueva; `eye`/`eye-off` ya incluidos en `allIcons`.
