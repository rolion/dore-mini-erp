# REV-2026-10-30-habilitar-produccion-y-costeo-02: Carrera al habilitar Costeo puede ejecutar el gancho de adopción dos veces

**Status:** Open
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-habilitar-produccion-y-costeo.md (v1)
**Spec reference:** AC-05 («invoca el gancho con empresa y fecha una sola vez»); EDGE-01
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
`EnableModule.execute` lee `enabled_keys()` y decide `key not in enabled` sin bloqueo de fila; `repository.enable` usa `get_or_create`. Dos peticiones simultáneas de habilitar Costeo pueden pasar ambas la comprobación y ejecutar `on_enabled` dos veces (la segunda con la fecha de la fila ya creada).

## Expected behavior
El gancho de valoración se ejecuta una sola vez por habilitación, también bajo concurrencia (p. ej. ejecutar el gancho solo si `get_or_create` creó la fila, o bloquear la fila de la empresa).

## Actual behavior
La idempotencia (EDGE-01) está garantizada de forma secuencial (probada), no bajo concurrencia. Riesgo bajo hoy porque la acción es de un admin y el gancho aún no tiene proveedor, pero se vuelve relevante cuando PB-VAL registre una valoración real.

## Evidence
`backend/modules/modularity/application/use_cases.py` (EnableModule.execute: `if key not in enabled: ... self.repository.enable(key); ... self.extensions.on_enabled(...)`) y `repositories.py` (`enable` devuelve `None`, no informa si creó la fila). No hay prueba de concurrencia.
