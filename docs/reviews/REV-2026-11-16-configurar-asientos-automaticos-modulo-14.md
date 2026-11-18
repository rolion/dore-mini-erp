# REV-2026-11-16-configurar-asientos-automaticos-modulo-14: Nombres de módulo, de método de pago y «Se comparte con» siguen en español en en/pt

**Status:** Resolved
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md (v4)
**Spec reference:** AC-14, API-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Cuarta pasada (revisión visual). AC-14 (v4) exige que los avisos, problemas de fila y errores 400 se muestren traducidos al idioma activo. Los textos con clave sí se traducen, pero tres datos que el backend envía como etiqueta en español se interpolan o se muestran tal cual.

## Expected behavior
En en/pt ningún texto del panel queda en español (salvo nombres que escribió la persona: cuentas y categorías). El módulo (`config.moduleLabel`, `shared_with[].label`) debería traducirse con `ACCOUNTING.POSTING.MODULES.<module>` (ya existe, ya se usa en «dónde corregir») y el método de pago con las claves existentes (`METODO_CASH`, `METODO_BANK_TRANSFER`, etc.) o nuevas.

## Actual behavior
- Introducción: EN «Choose the accounts Ventas will use…» / PT «…que Ventas usará…» / EN Inventario «Inventario will use».
- «Se comparte con»: EN «Shared with: Cobros.», «Shared with: Compras.»; PT «Compartilhada com: Cobros.», «Compartilhada com: Inventario.».
- Filas de método: etiquetas «Efectivo», «QR», «Transferencia», «Tarjeta», «Otro» en en/pt.
- Avisos: EN «The Asset account of the method “Transferencia” is missing. Set it in Sales › Settings › Automatic entries.» (módulo traducido, método no); idem PT («método «Tarjeta»»).
Es inconsistente: en la misma frase el lugar sale traducido y el método/módulo no.

## Evidence
Navegador (desktop 1280x720, ng serve 4315 + runserver 8011), idioma en/pt en /sales/settings, /purchases/settings, /inventory/settings y /expenses/settings; textos extraídos con `innerText` del `app-posting-config-panel`. Origen: `posting-config-panel.component.html` (`config.moduleLabel`, `row.label` en filas de método, `row.sharedWith` con `s.label`) y `posting-messages.ts` (`issue.params['method']`, `issue.subject` tras « · »).

## Resolution
El panel traduce el módulo (`MODULES.<módulo>`), los módulos que comparten un rol y los métodos de pago (`METHODS_LABEL.<código>`, con `method_code` en los avisos) en es/en/pt; el texto del servidor solo es respaldo. Pruebas: panel en inglés y `posting-messages.spec`.
