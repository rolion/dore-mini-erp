# REV-2026-11-26-registrar-diagnostico-odontograma-inicial-02: Confirmar una evaluación nueva que falla tras crear el borrador deja la UI en estado inconsistente

**Status:** Closed
**Severity:** Medium
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-11-26-registrar-diagnostico-odontograma-inicial.md (v1)
**Spec reference:** AC-11 («sin doble envío»), Edge case «Fallo de red al guardar: el formulario conserva lo escrito», UI-04
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`openConfirm` (`frontend/panel_admin/src/app/features/dentistry/pages/odontogram.component.ts:344-350`) ejecuta `persist().pipe(switchMap(evaluation => this.api.confirm(evaluation.id)))` dentro de `run()`. Para una evaluación nueva (`isNew`), `persist()` hace `api.create`; `applyEvaluation` solo se invoca en `next` del flujo completo (líneas 328-334). Si `create` tiene éxito y `confirm` falla (por ejemplo 400 «Registra al menos un hallazgo», 409 de cliente/perfil, o corte de red), el borrador ya existe en el servidor pero el componente conserva `isNew = true`, `current = null` y no refresca la lista (`refreshList` solo en éxito).

## Expected behavior
Tras el fallo la pantalla debe reflejar que el borrador ya fue creado (id, `sequence`, `allowed_actions`) para que reintentar confirme ese borrador, o bien crear y confirmar debe ser atómico.

## Actual behavior
El usuario ve el error pero la pantalla sigue en «nueva evaluación sin guardar»; el siguiente clic en Guardar/Confirmar vuelve a ejecutar `POST` de creación y recibe 409 («El paciente ya tiene la evaluación #n en borrador…»), y `hasDraft`/`canCreate` quedan desactualizados hasta recargar. No hay prueba que cubra este camino (`odontogram.component.spec.ts` no simula `confirm` fallido tras `create`).

## Evidence
Revisión de código (líneas citadas). Backend confirma el 409 de segundo borrador (`test_odontogram_api.py:117-119`). No se ejecutó en navegador (revisión visual no verificada).


## Verificación Quality Gate #2
Cerrado. `openConfirm` aplica la evaluación creada/guardada (`tap` → `applyEvaluation` + `refreshList`) antes de `confirm`; si confirmar falla, la pantalla ya refleja el borrador y el reintento lo confirma. Spec de componente añadida; Karma: 1936 SUCCESS.
