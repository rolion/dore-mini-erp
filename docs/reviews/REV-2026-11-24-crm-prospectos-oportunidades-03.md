# REV-2026-11-24-crm-prospectos-oportunidades-03: Sin contrato para listar usuarios de la empresa: el responsable solo se elige entre usuarios ya vistos

**Status:** Resolved
**Severity:** Low
**Category:** PLAN
**Related plan:** docs/plans/PLAN-2026-11-24-crm-prospectos-oportunidades.md (v1)
**Spec reference:** AC-02 («… y responsable»), AC-10 («filtros por responsable y prospecto/cliente»), INV-07; DDR («Prospecto/Cliente (búsqueda)»)
**Plan mode:** COMPLETO
**Suggested owner:** delivery-start

## Description
El API contract del plan valida `owner_id` contra los usuarios de la empresa, pero no define ningún endpoint para listarlos. La implementación lo resolvió así (está declarado como desviación en `## Implementación` del TASK):
- El selector de responsable del diálogo de oportunidad ofrece solo el usuario actual, el responsable de la oportunidad y los responsables de las tarjetas ya cargadas (`opportunity-dialog.component.ts` `ownerOptions`).
- Los filtros «Responsable» y «Prospecto/Cliente» del Kanban se arman con lo cargado en el tablero (`knownOwners`/`knownContacts`). No hay búsqueda libre, aunque el DDR la pedía para Prospecto/Cliente.

En consecuencia, desde la UI no se puede asignar una oportunidad a un compañero de la empresa que aún no es responsable de ninguna tarjeta del tablero. El backend sí lo permite.

## Expected behavior
O el plan define el contrato (p. ej. `GET /api/crm/users/` sobre `shared.identity.CompanyUserDirectory`, y búsqueda de prospecto/cliente para el filtro) y se implementa, o la Specification acepta explícitamente la limitación como deuda (decisión de negocio a confirmar con el usuario).

## Actual behavior
Con un solo usuario la limitación no se nota. Con varios usuarios, el responsable inicial de cualquier oportunidad nueva solo puede ser uno de los ya vistos.

## Evidence
TASK, `## Implementación`: «El plan no define endpoint de usuarios de la empresa: el selector/filtro de responsable ofrece el usuario actual y los responsables ya vistos en el tablero … (deuda: endpoint de usuarios y búsqueda libre)».
`frontend/panel_admin/src/app/features/crm/components/opportunity-dialog/opportunity-dialog.component.ts:151-154`:
```
  get ownerOptions(): CrmOwner[] {
    const all = [this.context.currentUser, this.context.opportunity?.owner, ...this.context.owners]
    ...
    return all.filter((owner, index) => all.findIndex((o) => o.id === owner.id) === index);
```

## Resolution
Nuevo `GET /api/crm/users/?search=` (`CrmUserListView`, sobre `shared.identity.CompanyUserDirectory`, solo `id` y `name`, empresa del usuario autenticado; probado con dos empresas, búsqueda y asignación como responsable). Frontend: `CrmUsersApiService`; el filtro «Responsable» y el diálogo ofrecen a todos los usuarios de la empresa; el filtro «Prospecto/Cliente» es un `ng-select` con búsqueda libre en prospectos y clientes. PLAN actualizado a v2 con la aprobación del usuario en el chat. Lint, `i18n:check` y 1901 pruebas Karma OK.
