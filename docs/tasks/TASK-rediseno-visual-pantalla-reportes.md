# TASK-rediseno-visual-pantalla-reportes: Rediseño visual de la pantalla de Reportes («Enfoque analítico visual»)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-rediseno-visual-pantalla-reportes
**Pull Request:** _sin abrir todavía_

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-18 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-18 | INVESTIGATION → DESIGN → PLANNING | Diseño requerido SI; sin arquitectura | delivery-start |
| 2026-11-18 | PLANNING → ENGINEERING | Specification READY | delivery-start |

## Investigación

### Requerimiento
Sesión padre: la rama `task/TASK-adaptar-reportes-libro-partida-doble` (PR #100, CONT-05, base `accounting`, sin mergear) añadió a `/pocketbiz/reports` el bloque «Libro contable» junto a las tarjetas operativas y la pantalla quedó desordenada. La crítica de diseño pide un rediseño «Enfoque analítico visual», solo frontend y sin cambios de API: (1) jerarquía por niveles y ancho máximo, con 2 KPIs contables grandes y 2 operativos pequeños, chips «Contable»/«Operativo» y encabezados de sección; (2) menos ruido: criterios largos plegados, tabla por cuenta plegada, textos ≥ 12 px con contraste AA, color solo con tokens, resultado negativo en rojo con etiqueta, `aria-label` en gráficos e iconos; (3) estados útiles: aviso «sin cuentas de dinero» con enlace a Contabilidad → Cuentas y aviso de cobertura cerrable que reaparece al cambiar de periodo. Etiquetas exactas: «Resultado», «Margen». Fuera de alcance: series por día, backend, submenú nuevo, renombrar «Ganancia estimada».

### Hechos encontrados
- `frontend/panel_admin/src/app/features/reporting/pages/reports/reports.component.html:18-76` — bloque contable con `h5` «Libro contable», aviso de cobertura (`alert-warning`, no cerrable) y dos tarjetas `col-lg-6` con tablas y criterio largo.
- `reports.component.html:78-102` — tarjetas operativas con tres `<small>` de criterio apilados; `:104-218` desgloses (canal con `progress`, dona `apx-chart` de 260 px, productos, clientes).
- `reports.component.ts:41` — la dona usa `foreColor: '#9aa0ac'` (HEX preexistente).
- `reports.component.ts:81-86` — `onSelection` recarga todas las fuentes: punto donde reiniciar el aviso cerrado.
- `report-card.component.html:1` — `card flex-grow-1`; no hay clase de altura igual en las columnas.
- `models/report.ts:66-89` — `LedgerReport.cashFlow.accounts` es la lista por cuenta.
- `backend/modules/accounting/domain/ledger_report.py:82-85` — `rows` se construye con **todas** las cuentas de dinero (con o sin movimiento) → `accounts` vacía ⇔ la empresa no tiene cuentas de tipo Caja/Banco/Billetera. La API actual basta para el aviso; no hay decisión abierta.
- `frontend/panel_admin/src/app/app.routes.ts:125` — ruta `accounting/accounts` (`/pocketbiz/accounting/accounts`).
- `reports.component.spec.ts` — specs con `data-testid` (`ledger-*`, `sales-*`, `expenses-*`, `*-table`, `*-empty`) que se deben conservar.
- `docs/design/design-system.md` §5 «Dashboard y reportes», §7 accesibilidad; alerta tenue (`bg-info-subtle text-info-emphasis`) admitida.
- El worktree no tiene `node_modules` (se enlazará por junction desde otro worktree, sin instalar).

### Hipótesis / supuestos no confirmados
- «Chips = variante del selector de periodo»: se interpreta como estilo visual (pill con tokens), sin interacción, porque no filtran nada; el objetivo táctil ≥ 40 px se aplica a los controles interactivos (selector de periodo, «Ver por cuenta», «¿Cómo se calcula?», cerrar aviso).
- Un resultado exactamente 0 se muestra neutro.

### Módulos y dependencias relacionadas
Solo `features/reporting` (frontend) e i18n `assets/i18n/{es,en,pt}.json`; enlace a `features/accounting` solo por URL.

### Implementaciones similares existentes
`features/reporting/pages/dashboard` (tarjetas de cifras); alerta tenue y `app-status-badge` en accounting.

### Comportamiento actual
Seis bloques al mismo nivel visual, criterios largos siempre visibles, tabla por cuenta siempre abierta, aviso de cobertura permanente, sin aviso de falta de cuentas de dinero (solo «Sin registros»).

### Restricciones
Sin HEX nuevos, tokens/clases del tema, `translate` en es/en/pt, reutilizar `app-report-card` y `app-period-selector`, sin cambios de contrato ni backend, PR con base `accounting`.

### Riesgos identificados
- El PR #100 sigue abierto: el diff incluye sus commits hasta que se mergee.
- Cambios de estructura HTML pueden romper specs por selectores (se conservan los `data-testid`).

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a una pantalla y sus textos, sin decisión arquitectónica ni de dominio nueva.

### Diseño requerido
**SI** — pantalla afectada con cambio de jerarquía visual y estados nuevos.

## Diseño
DDR: `docs/design/DDR-rediseno-visual-pantalla-reportes-jerarquia-analitica.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-18-rediseno-visual-pantalla-reportes.md` (v1, COMPLETO por DDR con impacto visual relevante).

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
