# REV-2026-11-27-crm-integracion-whatsapp-cloud-api-04: Pantalla de WhatsApp se aparta del DDR/UI-01 y de accesibilidad (UI-03)

**Status:** Open
**Severity:** Low
**Category:** DESIGN
**Related plan:** docs/plans/PLAN-2026-11-27-crm-integracion-whatsapp-cloud-api.md (v1)
**Spec reference:** UI-01, UI-02, UI-03; DDR pantalla de integracion WhatsApp; design-system seccion 8
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Desviaciones de la pantalla respecto al DDR y UI-03 que el apartado «Implementacion» no declara: (1) bloques en tarjetas apiladas, sin pestanas (UI-01 «Listados en pestanas»); (2) plantilla elegida con `<select>` nativo, el DDR indica `ng-select`; (3) los dos botones «Copiar» tienen el mismo texto y ningun `aria-label` que indique que copian (UI-03 «accesos con aria-label»); (4) la entrada de menu en `routes.json` no lleva `adminOnly` aunque el DDR dice que solo el administrador ve el menu (el backend si impone 403); (5) el texto SIN_CONEXION muestra una ruta de archivo del repositorio (`docs/integrations/...`) en vez de un enlace; (6) el submenu «Integraciones» del DDR queda plano bajo Configuracion (solo en breadcrumb).

## Expected behavior
Pantalla conforme al DDR o desviaciones declaradas y justificadas; botones con nombre accesible distinto; menu solo para administradores.

## Actual behavior
Ver descripcion. No se pudo verificar visualmente a 390/1440 px (ver informe: no se levanto la app para no migrar la BD de desarrollo compartida); la revision de la UI se hizo por lectura de plantilla y pruebas Karma.

## Evidence
`frontend/panel_admin/src/app/features/settings/pages/whatsapp-integration/whatsapp-integration.component.html` (botones copiar, select nativo, sin tabs); `frontend/panel_admin/src/assets/data/routes.json` (entrada sin adminOnly); `frontend/panel_admin/src/assets/i18n/es.json` clave SETTINGS.WHATSAPP.SIN_CONEXION. Nota: la entrada vecina `settings/modules` tampoco es adminOnly (consistente con lo existente).
