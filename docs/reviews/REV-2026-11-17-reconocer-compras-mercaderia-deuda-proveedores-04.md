# REV-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores-04: El TASK dice «SCSS copiado» pero el aviso importa el parcial de Contabilidad

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-17-reconocer-compras-mercaderia-deuda-proveedores.md (v1)
**Spec reference:** UI-01, docs/design/design-system.md sección 8 (checklist); TASK ## Implementación
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El TASK declara «SCSS copiado en reception-form.component.scss» y deuda «SCSS duplicado entre Ventas y Compras», pero el archivo hace `@use '../../../accounting/components/alert-warning'` (igual que `delivery-dialog` de Ventas) y solo agrega reglas locales. La documentación no refleja el código; además la revisión visual (contraste del aviso, tema oscuro, enlace) no pudo hacerse sin backend y sesión: queda «no verificada».

## Expected behavior
TASK coherente con el código; revisión visual del aviso en claro/oscuro antes de aprobar.

## Actual behavior
Inconsistencia documental menor; sin impacto funcional.

## Evidence
```
frontend/panel_admin/src/app/features/purchases/pages/reception-form/reception-form.component.scss:2
@use '../../../accounting/components/alert-warning';
```
