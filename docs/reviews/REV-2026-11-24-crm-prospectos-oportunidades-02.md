# REV-2026-11-24-crm-prospectos-oportunidades-02: Faltan las pruebas planificadas de concurrencia y de la restricción única de pedido en BD

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-prospectos-oportunidades.md (v1)
**Spec reference:** Test Specification › Integration tests («conversión … idempotente / concurrencia simulada»); INV-06; Risks («pedido vinculado en carrera (unicidad en BD)»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
El plan pide probar la conversión con «concurrencia simulada» y presenta la restricción única condicional `crm_opportunity_order_unique` como respaldo ante carreras. El código lo maneja: `DjangoOpportunityRepository.save` captura el `IntegrityError` de esa restricción en un savepoint y lo traduce a `CrmConflict('order_already_linked')`, y la conversión bloquea el prospecto con `select_for_update`. Pero ninguna prueba ejecuta esos caminos:
- `test_api_leads.py` solo prueba la idempotencia secuencial (segundo POST, `# doble clic / reintento`).
- `test_each_rejection_code` llega a `order_already_linked` por la verificación previa de aplicación (`opportunity_for_order`), no por la restricción de BD. La traducción del `IntegrityError` (que depende de `exc.__cause__.diag.constraint_name`) no se ejecuta nunca.
- Los `CheckConstraint` de `crm_opportunity` tampoco tienen prueba directa.

## Expected behavior
Al menos una prueba que guarde, por el repositorio, una segunda oportunidad con un `order_id` ya usado y obtenga `CrmConflict('order_already_linked')` con la transacción utilizable. Además, la conversión con concurrencia simulada que pide el plan (p. ej. prospecto ya convertido entre la lectura y el bloqueo, o una prueba que verifique el `select_for_update`), o una desviación justificada en `## Implementación`.

## Actual behavior
Los caminos de carrera solo quedan cubiertos por lectura de código. La suite pasa (616 pruebas), pero un cambio en el driver o en el nombre de la restricción rompería la traducción a 409 sin que falle ninguna prueba.

## Evidence
```
$ grep -rniE "carrera|race|doble|IntegrityError|order_unique|simulad" backend/modules/crm/tests
crm/tests/test_api_leads.py:96:        again = self.convert(lead['id'])  # doble clic / reintento
```
`backend/modules/crm/infrastructure/django/repositories.py` (`DjangoOpportunityRepository.save`):
```
        except IntegrityError as exc:
            name = getattr(getattr(exc.__cause__, 'diag', None), 'constraint_name', None)
            if name != 'crm_opportunity_order_unique':
                raise
            raise CrmConflict('order_already_linked', 'El pedido ya está vinculado a otra oportunidad.') from exc
```
