# REV-2026-11-04-refinar-ux-pacientes-odontologia-06: Aviso «Perfil creado» redactado como «Paciente creado. Puedes completar…»

**Status:** Resolved (el copy de la UI se alineó con el AC-03 «Perfil creado»; la Specification no cambia)
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md (v1)
**Spec reference:** AC-03 (aviso «Perfil creado»), Ubiquitous language
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
AC-03 y el glosario usan «Perfil creado»; la clave PERFIL_ODONTOLOGICO_CREADO de es.json dice «Paciente creado. Puedes completar los antecedentes ahora o más tarde.» (el registro de cambios sí usa «Perfil creado»).

## Expected behavior
Texto alineado con la especificación, o la especificación actualizada si el nuevo copy es el deseado.

## Actual behavior
Divergencia de copy entre el AC y la UI; no afecta la funcionalidad.

## Evidence
es.json DENTISTRY.PATIENT_DETAIL.PERFIL_ODONTOLOGICO_CREADO = "Paciente creado. Puedes completar los antecedentes ahora o más tarde."; DENTISTRY.PATIENT_HISTORY.ALTA = "Perfil creado".
