# REV-2026-10-30-reportes-adaptar-modulos-activos-02: Documentación de arquitectura y design-system quedó desactualizada

**Status:** Resolved (corregido en delivery-build, ciclo 2)
**Severity:** Low
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-30-reportes-adaptar-modulos-activos.md (v1)
**Spec reference:** Plan: Files/components affected (docs/architecture/ddd.md; design-system §5), DDR Consecuencias
**Plan mode:** COMPLETO
**Suggested owner:** delivery-engineer

## Description
El plan lista `docs/architecture/ddd.md` (nota de módulos) como archivo afectado, pero el diff no lo modifica: la línea 844 sigue diciendo "Mapa: ... reporting→sales, expenses" (dependencias obligatorias), y la línea 819 no cambia (reporting→{sales,expenses,customers} sigue válida como mapa de imports). Además `docs/design/design-system.md:126` conserva "los vacíos dicen \"Sin datos para este periodo.\"" justo encima de la línea nueva que dice "Sin registros", y el DDR ordena reemplazar ese texto.

## Expected behavior
ddd.md refleja que Reportes no requiere Ventas/Gastos (opcionales, PB-REP-001); design-system §5 tiene una sola regla de vacíos («Sin registros»).

## Actual behavior
Dos documentos contradicen el comportamiento implementado.

## Evidence
```
docs/architecture/ddd.md:844: ... Mapa: sales→catalog; reporting→sales, expenses; purchases→catalog, expenses; inventory→catalog. ...
docs/design/design-system.md:126: ... y los vacíos dicen "Sin datos para este periodo."
docs/design/design-system.md:127: - Fuente deshabilitada: ... Fuente activa sin datos: ... **«Sin registros»**
```
