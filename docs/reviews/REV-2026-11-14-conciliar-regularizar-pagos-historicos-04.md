# REV-2026-11-14-conciliar-regularizar-pagos-historicos-04: Reglas de mapeo incompletas se descartan en silencio al enviar

**Status:** Resolved
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-14-conciliar-regularizar-pagos-historicos.md (v2)
**Spec reference:** UI-02, UI-05
**Plan mode:** COMPLETO
**Suggested owner:** delivery-frontend

## Description
`toRequest` (`features/accounting/models/regularization.ts`) omite sin aviso toda regla sin método o sin cuenta (incluida una con fechas «desde/hasta» rellenadas).

## Expected behavior
La persona ve que una regla está incompleta (error de campo o aviso) y no que la previsualización asume que no existe.

## Actual behavior
Una regla a medias desaparece del cuerpo; esos pagos salen como «pendientes» sin indicar que se debió a una regla ignorada. Es seguro (nunca crea entradas con cuenta inferida) pero confuso. Relacionado: con cero reglas la UI envía `mapping: {}` y el backend responde 400 («El mapeo debe ser un objeto … no vacío»), mientras que el comando permite previsualizar sin mapeo; además los mensajes 400 del servidor están en español y se muestran tal cual en en/pt, y la tabla de casos a revisar formatea el importe con la moneda fija `'BOB'`.

## Evidence
`toRequest`: `if (!rule.method || !rule.accountId) { continue; }`. `parse_mapping`: `if not isinstance(raw, dict) or not raw: raise RegularizationInputError(...)`. `regularization.component.html`: `money(detail.amount, 'BOB')`.

## Resolución
Reglas a medias: la pantalla avisa y no previsualiza. Sin reglas: la API previsualiza (todo pendiente) y rechaza aplicar con 400. La tabla de revisión usa la moneda de cada pago (`currency` en el detalle). Los mensajes 400 del servidor salen en español también en en/pt: es el comportamiento de toda la API del proyecto, se acepta como limitación.
