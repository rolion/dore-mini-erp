# REV-2026-11-24-crm-tableros-columnas-configurables-01: `target_stage_id` ajeno responde 400, el AC-08 pide 404

**Status:** Open
**Severity:** Low
**Category:** SPECIFICATION
**Related plan:** docs/plans/PLAN-2026-11-24-crm-tableros-columnas-configurables.md (v1)
**Spec reference:** AC-08 («ids de tablero/etapa de otra empresa (en ruta o en `target_stage_id`) → 404») vs. API-06 («400 destino inválido»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El PLAN es internamente contradictorio: AC-08 exige 404 para un `target_stage_id` de otra empresa, mientras API-06 dice 400 para destino inválido. La implementación eligió 400 (no revela la existencia del id ajeno; es idéntico a un destino inexistente) y el test `test_other_company_ids_are_404_everywhere` lo fija en 400. La «desviación» declarada en `## Implementación` del TASK solo menciona que el destino inválido se rechaza aunque la etapa no tenga tarjetas; no declara que un destino ajeno incumple el texto literal de AC-08.

## Expected behavior
Un criterio de aceptación sin ambigüedad: o bien 404 para destino ajeno (AC-08 literal), o bien AC-08/API-06 reconciliados en el plan (400 para `target_stage_id`) y la desviación declarada.

## Actual behavior
`POST /api/crm/boards/<mi_tablero>/stages/<mi_etapa>/archive/` con `target_stage_id` de otra empresa -> 400 `{"target_stage_id": [...]}`; nada cambia (verificado por el test). No hay fuga de datos entre empresas.

## Evidence
- backend/modules/crm/tests/test_api_boards.py:166 `self.assertEqual(target.status_code, 400)  # un destino ajeno nunca resuelve...`
- backend/modules/crm/domain/board.py `validate_stage_archive`: destino no encontrado -> `BoardValidationError({'target_stage_id': ['Elige una etapa activa de este tablero.']})`.
- Menor relacionado: el mapeo AC-01 del PLAN cita «test de registro de empresa», pero ningún test de `modules/accounts` verifica el tablero «Ventas» tras registrarse (solo `crm/tests/test_defaults.py` vía `apply_all`; `registration.py:45` sí llama `apply_all`).
