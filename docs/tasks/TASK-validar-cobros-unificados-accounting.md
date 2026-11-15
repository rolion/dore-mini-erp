# TASK-validar-cobros-unificados-accounting: Validar cobros unificados y preparar la activación de accounting (PB-ACC-005)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** NO
**Rama:** task/TASK-validar-cobros-unificados-accounting
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/72
**Fuente:** https://trello.com/c/F2bSta2n/22-pb-acc-005-validar-cobros-unificados-y-preparar-activaci%C3%B3n-de-accounting

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-15 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta; `main` al día (6b4f7d1, incluye PB-ACC-001..004 y PB-COB-002) | delivery-start |
| 2026-11-15 | INVESTIGATION → PLANNING | NEEDS_PLAN: sin decisión arquitectónica nueva ni pantallas; es validación, pruebas de brechas y runbook | delivery-start |
| 2026-11-15 | PLANNING → ENGINEERING | Specification READY: la tarjeta fija los criterios; sin decisiones de negocio abiertas | delivery-start |

## Investigación

### Requerimiento
Insumo de la tarjeta PB-ACC-005 (P1, cierre de entrega; **no es una Specification aprobada**). Objetivo: validar que configuración, libro, cobros e históricos funcionan como un único recorrido antes de activar accounting. Alcance: revisar las pruebas de integración ya añadidas (atomicidad, idempotencia, concurrencia, permisos, aislamiento) y completar **solo brechas**; verificar en interfaz productos y odontología, incluidos perfiles con Ventas deshabilitado; no cambiar reporting (ventas − gastos intacto; Entradas = dinero recibido por fecha del pago, productos y servicios diferenciados); preparar instrucciones concretas (configurar cuentas y métodos, validar contratos y permisos, previsualizar regularización, aplicar, comprobar totales); documentar cobertura histórica, pendientes y reversiones fuera de alcance. No desplegar ni regularizar producción. Criterios: productos Bs 300 en 100+200; servicios Bs 300 en 100+50+150; libro Bs 600 (300/300) sin duplicados; una distribución por varias líneas = una entrada; reintento/fallo contable/falta de mapeo/concurrencia coherentes; cambio de mapeo conserva históricos; perfil odontológico cobra con Ventas deshabilitado, stock no cambia y notas clínicas no llegan al libro; regularización repetida no altera totales; listado y totales coinciden con filtros en todas las páginas; reporte ventas − gastos intacto y cuentas no presentadas como saldos bancarios; accounting deshabilitado conserva el comportamiento actual. Dependencia: PB-ACC-004 (ya en `main`).

### Hechos encontrados
- Pagos de productos con libro: `backend/modules/sales/tests/test_payment_ledger.py` cubre AC-01..AC-11 de PB-ACC-003 (dos pagos → dos entradas, idempotencia, concurrencia `:305-311`, falta de mapeo `:123`, fallo del libro `:138`, cambio de mapeo `:155`, accounting deshabilitado `:162`, aislamiento `:174`, cancelación conserva pagos `:84`).
- Pagos de servicios con libro: `backend/modules/receivables/tests/test_payment_ledger.py` cubre anticipo+abono+final 100/50/150 (`:47`), distribución con una entrada (`:58`), dental (`:77`), totales por la API (`:94`), reintento (`:110`), concurrencia (`:119`, `:140`), mapeo ausente (`:162`), fallo del libro (`:180`), otra empresa (`:196`), accounting deshabilitado (`:210`), **Ventas deshabilitado** (`:248`).
- Libro: `backend/modules/accounting/tests/test_entries_api.py:60-85` (totales y filtros cubren todas las páginas), `:157` (no admin), `:173` (sin escritura manual).
- Regularización: `accounting/tests/test_regularization.py` (20) y `test_regularization_api.py` (4): previsualización sin escritura, segunda pasada, conflictos, concurrencia, aislamiento.
- **Brechas observadas** (por búsqueda, a confirmar al escribir las pruebas): (1) ningún test reúne en una misma empresa pedido de productos Bs 300 (100+200) y proforma de servicios Bs 300 (100+50+150) y comprueba `totals` = 600 con `by_origin` PRODUCT 300 / SERVICE 300 sin duplicados; (2) no hay prueba de que cobrar un pedido no mueve stock (`StockMovementModel` se usa solo en `sales/tests/test_delivery_inventory.py`); (3) ninguna prueba afirma que las notas clínicas no llegan al libro (campos de la entrada); (4) regularización + cobro nuevo + listado/totales en una sola secuencia (tras regularizar y repetir, totales y saldos idénticos), y que el listado del libro coincida con filtros tras regularizar; (5) reporte ventas − gastos sin cambio con el libro habilitado (`backend/modules/reporting/tests/` no menciona accounting); (6) la API del libro no expone saldos (no hay campo `balance`) — solo totales de entradas.
- No existe documento operativo de activación: `docs/deployment/` solo tiene `docker.md` y `github-actions.md`; `docs/tests/MANUAL-*.md` es el patrón de guías de verificación manual.
- Interfaz: `frontend/panel_admin/src/app/features/accounting/pages/{accounting-settings,entry-list,entry-detail,regularization}`; no hay carpeta E2E (Playwright no instalado).

### Hipótesis / supuestos no confirmados
- El reporte actual es `modules/reporting` (ventas − gastos); se confirma su ubicación y etiqueta al escribir la prueba de regresión.
- «Verificar en interfaz» se cumple con una guía manual ejecutada en el navegador integrado con datos de desarrollo; no se instala Playwright.

### Módulos y dependencias relacionadas
`accounting`, `sales`, `receivables`, `dentistry`, `inventory`, `reporting`, `modularity`; frontend `features/accounting`.

### Implementaciones similares existentes
`docs/tests/MANUAL-ventas-inventario-salida-al-entregar.md` (guía manual), pruebas de integración por módulo citadas arriba.

### Comportamiento actual
Cada tarea probó su tramo; falta una validación de punta a punta y el runbook de activación.

### Restricciones
`CLAUDE.md`: `Decimal`, `company_id`, sin editar migraciones aplicadas, no tocar `.env` ni producción, avisar antes de instalar dependencias. Sin cambios de comportamiento de producto: si una prueba revela un defecto, se reporta como hallazgo y se corrige solo si es mínimo y está en alcance.

### Riesgos identificados
Que la validación descubra un defecto real (se corrige o se documenta como pendiente); duplicar pruebas ya existentes (se limita a brechas); pruebas intermitentes preexistentes (`TASK-pruebas-intermitentes`).

### Veredicto de complejidad
**NEEDS_PLAN** — pruebas y documentación sobre comportamiento ya implementado; sin contrato, migración ni decisión estructural nuevos.

### Diseño requerido
**NO** — no hay pantallas nuevas; la verificación de interfaz usa las existentes.

## Diseño
No aplica.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-15-validar-cobros-unificados-accounting.md` (v1, COMPLETO por frontera cruzada) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
