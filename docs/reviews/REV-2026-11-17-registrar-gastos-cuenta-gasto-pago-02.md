# REV-2026-11-17-registrar-gastos-cuenta-gasto-pago-02: La Specification (INV-03) y el ADR dicen cuenta de pago de clase Activo; la implementacion exige cuenta de dinero

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-17-registrar-gastos-cuenta-gasto-pago.md (v1)
**Spec reference:** INV-03, AC-02; ADR decision 1
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
INV-03 define la cuenta de pago como "clase Activo". La implementacion agrega `money_account_problem`: la cuenta elegida debe ser Caja/Banco/Billetera (`kind` informado). La decision es razonable (la tarjeta pide Caja/Banco) y esta declarada como desviacion en el TASK, pero PLAN, ADR y Specification no se actualizaron.

## Expected behavior
La Specification (INV-03, AC-02) y el ADR reflejan la regla vigente, con un caso de prueba nombrado en la tabla de verificacion.

## Actual behavior
Documentos con la regla antigua; el codigo rechaza p. ej. "Cuentas por cobrar" como cuenta de pago (verificado por el revisor: 400 `payment_account_id`, "no es de dinero (Caja, Banco o Billetera)"). Solo se aplica a overrides, no a la cuenta por defecto de la configuracion.

## Evidence
- `backend/modules/accounting/domain/posting.py` (`money_account_problem`, `validate_account_for_role(money_only=True)`).
- Sonda: `CXC-AS-PAY 400 {"payment_account_id":["La cuenta «Cuentas por cobrar» no es de dinero ..."]}`.
