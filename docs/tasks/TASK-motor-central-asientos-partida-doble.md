# TASK-motor-central-asientos-partida-doble: Motor central de asientos con partida doble, reversión e idempotencia (CONT-02)

**Etapa actual:** ENGINEERING
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** task/TASK-motor-central-asientos-partida-doble
**Pull Request:** _sin abrir todavía_
**Fuente:** https://trello.com/c/hRlnoPrC/3-cont-02-implementar-motor-central-de-asientos-con-partida-doble-reversi%C3%B3n-e-idempotencia

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado; base = rama `accounting` (fast-forward a `origin/accounting`, PR #82) | delivery-start |
| 2026-11-16 | INVESTIGATION → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE, diseño NO (solo backend; UI en CONT-11) | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |

## Investigación

### Requerimiento
Tarjeta Trello CONT-02 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.
- Reemplazar el movimiento de una sola cuenta por un **asiento** con cabecera y varias líneas.
- Cabecera: empresa, fecha contable, descripción, origen manual/automático, referencia única de evento, usuario, período y vínculo de reversión.
- Líneas: cuenta de la misma empresa; Debe **o** Haber positivo (nunca ambos); mínimo dos cuentas distintas; Σ Debe = Σ Haber > 0 con decimal exacto.
- Validar cuentas habilitadas y período abierto; guardar cabecera, líneas y operación de origen **atómicamente**.
- Unicidad en base por empresa/origen/evento; reintentos y concurrencia sin duplicados; dos operaciones legítimas iguales pueden coexistir con IDs de evento distintos.
- Confirmados inmutables. Reversión completa: invierte Debe/Haber de todas las líneas, vincula el original, exige motivo y fecha, ocurre una sola vez; no se borra el original ni se editan automáticos. Usa las cuentas originales aunque estén deshabilitadas; si el período original está cerrado se registra en un período abierto con fecha explícita; no se reclasifica como ingreso/gasto nuevo.
- «Sustituir el contrato anterior según CONT-07, sin doble contabilización durante la transición».
- Pruebas de aceptación de la tarjeta: (1) Debe Caja 200 + Banco 300 / Haber Ingresos 500 confirma; 499 rechaza sin persistir; (2) rechazar una sola cuenta, importes negativos, línea con ambos lados, cuenta ajena y período cerrado; (3) reintentos concurrentes generan un solo asiento y un fallo de línea revierte origen y cabecera; (4) revertir una vez neutraliza todas las líneas y dos solicitudes simultáneas no duplican.
- Dependencias: CONT-07, CONT-09, CONT-10 (las tres hechas). Transversal: aislamiento por empresa, permisos existentes, decimales/moneda existentes, sin conversión de divisas.

### Hechos encontrados
- No existe ningún asiento: Contabilidad es un libro de **entradas de una sola cuenta**: `backend/modules/accounting/domain/entry.py:59` (`Entry`), `infrastructure/django/models.py:109` (`EntryModel`, único `(company, origin_kind, origin_id, operation)` en `models.py:141`, reversión 1:1 vía `reverses`).
- Fachada pública `backend/modules/accounting/services.py:155` (`record_entry`) y `:190` (`reverse_entry`): exigen transacción abierta (`connection.in_atomic_block`), bloquean la cuenta con `FOR UPDATE`, son idempotentes por origen y lanzan `EntryConflict` si los datos difieren.
- Llamantes actuales del contrato anterior: `sales/infrastructure/adapters.py`, `receivables/infrastructure/adapters.py` y `accounting/infrastructure/adapters.py:57` (regularización). Sus tarjetas de migración (VEN-01, SRV-01, COM-01/02, INV-01, GAS-01/02) están por hacer.
- Períodos (CONT-10): `services.py:274` `lock_open_period(company_id, fecha)` bloquea la fila del período con `FOR UPDATE` y lanza `DateOutsideFiscalPeriod` / `FiscalPeriodClosed`; `period_for` lee sin bloquear (`services.py:268`). Cerrar toma el mismo bloqueo (`repositories.py:431`).
- Puerto `PeriodUsage` con adaptador provisional `NoJournalPeriodUsage` (`infrastructure/adapters.py:77`, usado en `api/views.py:329`): **CONT-02 debe reemplazarlo** por uno que cuente asientos fuera del nuevo rango (TASK-periodos-fiscales-por-empresa, «Deuda / pendiente para CONT-02»; AC-08/AC-09 por probar con asientos reales).
- Cuentas (CONT-08/09): `Account` con `code`, `account_class` (ASSET…COST), `is_active`, `currency`, `is_contra` (`domain/account.py:107`); clasificaciones habilitables por empresa (`domain/account_class.py:34` `ensure_enabled`, `DjangoAccountClassRepository.disabled()`). `account_class` y `code` siguen siendo nulos en cuentas anteriores.
- Monedas: `CURRENCIES = ('BOB','USD')`, dinero `DecimalField(12,2)` (`domain/catalog.py:15`, `entry.py:16-17`).
- Contrato de transición (CONT-07): `docs/adr/ADR-diagnostico-transicion-partida-doble-estrategia-y-contrato.md` — migraciones solo aditivas, **conversión de datos por comando explícito en la Etapa 2** (con mapeos del dueño), nunca dentro de `migrate`; asientos convertidos conservarán `origin_kind/origin_id/operation`.
- Patrón de concurrencia en pruebas: `tests/test_fiscal_period_concurrency.py`, `tests/test_entry_concurrency.py` (`_run_together`). Migraciones accounting: lineales hasta `0009_fiscal_period`.
- Reglas de arquitectura: `docs/architecture/ddd.md` (dominio sin Django; módulos solo por `services.py`; estados cambian por métodos del agregado).
- Otras tarjetas fijan el alcance vecino: **CONT-11** (UI de movimientos, formulario manual y reversión «usando CONT-02»), **CONT-12** (configuración de automáticos por módulo), **CONT-04/05** (saldos y reportes sobre el nuevo libro), **CONT-13** (conciliación y migración). El motor no lleva UI.

### Hipótesis / supuestos no confirmados
- «Cuenta habilitada» = activa, con código y clasificación contable asignada y **habilitada en la empresa**. Las cuentas anteriores sin clasificación o código se rechazan para asientos nuevos (hasta que se completen en CONT-09).
- Todas las líneas de un asiento comparten la **moneda** de sus cuentas (sin conversión): cuentas de monedas distintas en un mismo asiento se rechazan.
- «Origen automático» se identifica con `(origin_kind, origin_id)`; el vocabulario de `origin_kind` del motor es nuevo y lo definen los módulos en sus tarjetas (VEN-01…); el motor solo exige formato.
- La fecha de reversión no tiene regla adicional respecto a la del original (solo debe caer en un período abierto): la tarjeta no pide `≥`.
- «Sustituir el contrato anterior» se interpreta como **coexistencia aditiva con corte limpio por origen**, no como reescribir ya a los llamantes (decisión en el ADR).

### Módulos y dependencias relacionadas
Solo `accounting` (nuevo agregado `JournalEntry`). Sin dependencias nuevas entre módulos. Consumidores futuros: `sales`, `receivables`, `purchases`, `expenses`, `inventory` por `accounting.services`.

### Implementaciones similares existentes
`Entry`/`record_entry`/`reverse_entry` (idempotencia por origen con `IntegrityError` en punto de guardado), `FiscalPeriod` + `lock_open_period` (bloqueo), `DjangoAccountRepository.get_for_update`.

### Comportamiento actual
Cada cobro/egreso es una fila `accounting_entry` con una cuenta y una dirección; no hay partida doble, descripción, período ni líneas.

### Restricciones
`CLAUDE.md`: dinero `Decimal`, nunca editar migraciones aplicadas (nueva `0010`), aislamiento por `company_id`, dominio sin Django, sin dependencias nuevas, i18n no aplica (sin UI nueva).

### Riesgos identificados
- Doble contabilización entre el libro de entradas y el nuevo libro durante la transición (mitigado en el ADR).
- Carreras: reintentos simultáneos del mismo evento, doble reversión, cierre de período vs. asiento.
- Que la suma Debe=Haber solo se pueda garantizar en dominio (no hay `CHECK` multi-fila); se mitiga con inserción atómica única y con una prueba de conciliación.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — tablas y migración nuevas, contrato transaccional que consumirán varios módulos, concurrencia con bloqueos y decisión sobre la coexistencia con el contrato anterior.

### Diseño requerido
**NO** — solo backend/contrato de fachada; la pantalla de movimientos, el formulario manual y la confirmación de reversión son CONT-11.

## Diseño
No aplica (sin UI).

## Arquitectura
`docs/adr/ADR-motor-central-asientos-partida-doble-modelo-y-contrato.md`

## Plan
`docs/plans/PLAN-2026-11-16-motor-central-asientos-partida-doble.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
_Pendiente_

## Review
_Pendiente_

## Publicación
_Pendiente_
