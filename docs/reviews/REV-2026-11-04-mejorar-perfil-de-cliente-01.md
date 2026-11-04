# REV-2026-11-04-mejorar-perfil-de-cliente-01: Objetivo táctil ≥ 44 px en móvil solo cubierto para los enlaces de la tabla

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-04-mejorar-perfil-de-cliente.md (v1)
**Spec reference:** AC-09 (vista móvil y accesibilidad); DDR-mejorar-perfil-de-cliente-perfil-accionable, sección «Accesibilidad» ("objetivos táctiles ≥ 44 px en móvil"); Non-functional requirements ("objetivos ≥ 44 px en móvil")
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan y el DDR exigen objetivos táctiles de al menos 44 px en móvil. La implementación solo fuerza `min-height: 44px` en los enlaces de las celdas de la tabla apilada del historial (`customer-purchase-history.component.scss`, regla `td a`, dentro de `@media (max-width: 767.98px)`). El resto de controles táctiles nuevos usan `btn-sm` de Bootstrap sin ajuste móvil:

- botón «WhatsApp» (`btn btn-light btn-sm`) en `customer-detail.component.html`;
- enlace «Ver todos los pedidos» (`btn btn-light btn-sm`) en `customer-purchase-history.component.html`;
- enlaces `tel:` y `mailto:` (texto en línea, sin altura mínima).

Los botones `btn` normales de la cabecera (Nuevo pedido, Editar, Desactivar) no se midieron: la revisión visual en navegador no se pudo hacer (no hay backend levantado).

## Expected behavior
En viewport móvil, todo botón o enlace accionable del perfil mide al menos 44 px de alto, o hay una excepción documentada.

## Actual behavior
`btn-sm` de Bootstrap 5 mide unos 31 px de alto. Ninguna prueba ni estilo cubre los controles de contacto y «Ver todos los pedidos». Ninguna prueba verifica el tamaño (AC-09 solo se prueba por marcado: `caption`, `scope`, `aria-label`).

## Evidence
`customer-purchase-history.component.scss`, regla final:

```
// Objetivo táctil cómodo para abrir el pedido.
td a {
  display: inline-block;
  min-height: 44px;
  line-height: 44px;
}
```

`grep` de `min-height`/`44px` en los archivos del PR: solo esa regla. Los elementos `btn btn-light btn-sm` aparecen en `customer-detail.component.html` (WhatsApp) y `customer-purchase-history.component.html` (Ver todos). No verificado en navegador (sin backend); el incumplimiento se infiere del código y de la altura estándar de `btn-sm`. La confirmación visual debe hacerse en la revisión manual del paso 8 del plan.
