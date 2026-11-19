# TASK-configuracion-contable-por-defecto-nueva-empresa: Configuración contable y de módulos por defecto en empresas nuevas

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** NO
**Rama:** `task/TASK-configuracion-contable-por-defecto-nueva-empresa` (base: `accounting`)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/109

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-19 | (nuevo) → INVESTIGATION | Task creado | delivery-start |
| 2026-11-19 | INVESTIGATION → ARCHITECTURE → PLANNING | Veredicto NEEDS_ARCHITECTURE; decisiones de negocio respondidas por el usuario | delivery-start |
| 2026-11-19 | PLANNING → ENGINEERING | Specification READY, plan v1 | delivery-start |
| 2026-11-19 | ENGINEERING → REVIEW | Implementación completa según plan v1 | delivery-build |
| 2026-11-19 | REVIEW → PUBLISH | Quality Gate PASS (4 hallazgos Low/Medium no bloqueantes) | delivery-publish |

## Investigación

### Requerimiento
«En la base de datos doredb, el usuario demo demo y la empresa demo dore tienen configuradas las cuentas de contabilidad y la configuración de cada módulo. Quiero que esas cuentas y configuración se vuelvan el default al crear una nueva empresa, y también un script para copiar estas cuentas y configuración a una empresa específica.» Aclaración del usuario: **usar la rama `accounting` como base** de la tarea.

Decisiones del usuario (respondidas en el chat, 2026-11-19):
1. Fuente de los defaults: **snapshot JSON versionado en el repo** (no empresa plantilla viva).
2. Una empresa nueva recibe: plan de cuentas + mapeo de métodos + cuentas de asientos automáticos + clasificaciones; **los 14 módulos habilitados**; ajustes de módulo; categorías de gasto y almacén principal.
3. Fecha de corte = fecha de alta de la empresa; período fiscal = año en curso; saldos de apertura en 0.
4. Script de copia: **solo completa lo que falta** (idempotente, no pisa lo configurado), con `--dry-run`.

### Hechos encontrados
Lectura de solo consulta a `doredb` (empresa `demo dore`, id `279b9216-…`), sin modificar nada:
- 20 cuentas (`accounting_account`): códigos 1102 Bancos (BANK), 1103, 1104 + 110401–110405, 11101 Caja (CASH), 2101, 2104, 3101, 4101, 4102, 5101, 6101–6104, 6107; moneda BOB; saldos de apertura 0; ninguna contra.
- 5 mapeos de método de pago (`accounting_method_mapping`): CASH→11101; QR, CARD, BANK_TRANSFER, OTHER→1102.
- 10 cuentas de asientos automáticos (`accounting_posting_account`): 8 `ROLE` (SALES_INCOME, SERVICE_INCOME, RECEIVABLE, INVENTORY, COST_OF_SALES, PAYABLE, CUSTOMER_ADVANCES) y 3 `CATEGORY` cuya `key` es el **UUID de una categoría de gasto de esa empresa** (Sueldos→6101, Alquiler→6102, Servicios Básicos→6103).
- 7 clasificaciones (`accounting_classification`), 0 filas en `accounting_account_class_setting` (sin fila = habilitada), 1 `accounting_settings` (corte 2026-10-30), 1 período fiscal «2026» abierto, 1 tramo de cobertura abierto.
- 14 módulos habilitados (`modularity_company_module`): customers, sales, reporting, inventory, services, expenses, purchases, accounting, dentistry, personnel, agenda, receivables, quotations, costing.
- 2 ajustes (`modularity_company_setting`): `sales.default_sales_channel=WHATSAPP`, `sales.default_payment_method=QR`.
- `purchases_settings.payment_classification_id` apunta a una clasificación (UUID por empresa).
- 4 categorías de gasto (`expenses_category`): Sueldos y Salarios, Servicios Basicos, Pago a proveedores, Alquiler; 1 almacén «Almacén principal».
- `backend/modules/accounts/registration.py:27-49` — `register_company_admin` crea `Company` y su primer admin en una transacción; hoy no siembra nada.
- `backend/modules/modularity/infrastructure/django/repositories.py:16-28` — los módulos por defecto se siembran perezosamente desde `DEFAULT_ENABLED_KEYS` (`domain/modules.py:43` = customers, sales, expenses, reporting).
- `backend/shared/module_lifecycle.py` y `shared/enable_preconditions.py` — patrón existente de puertos neutros con registro al arrancar (`accounting/apps.py:13`); `accounting/infrastructure/lifecycle.py:28-37` abre el tramo de cobertura al habilitar.
- Modelos con `company_id` sin FK por módulo (`accounting/infrastructure/django/models.py:8-285`, `modularity/.../models.py:6-45`, `purchases/.../models.py:141`).
- `CLAUDE.md`: los módulos de negocio no importan `accounts`; los módulos no importan infraestructura entre sí.
- `inventory/application/use_cases.py:25-43` — `ensure_default()` ya crea el almacén principal de forma perezosa.

### Hipótesis / supuestos no confirmados
- Las cuentas de inventario 110401–110405 y 3101 no están en ningún rol de asientos; se copian igualmente por ser parte del plan de cuentas (se asume intencional).
- Las 7 clasificaciones se copian tal cual, incluida la inactiva «Alquiler / INCOME».
- «Pago Proveedores» es la clasificación apuntada por `purchases_settings` (se confirma al exportar; el snapshot guarda el nombre+dirección).

### Módulos y dependencias relacionadas
`accounts` (alta), `modularity` (módulos y ajustes), `accounting`, `expenses`, `purchases`, `inventory`. Cruza 6 bounded contexts.

### Implementaciones similares existentes
Puertos neutros en `shared/` registrados desde `apps.py` (`module_lifecycle`, `enable_preconditions`, `module_gate`); comandos de gestión en `accounting/management/commands/regularize_ledger.py` (preview sin `--apply`).

### Comportamiento actual
Una empresa nueva queda sin cuentas, sin mapeos ni clasificaciones, con 4 módulos y sin ajustes; Contabilidad no se puede habilitar sin mapeo de métodos completo.

### Restricciones
Aislamiento por `company_id`; no importar `accounts` desde módulos; dinero en `Decimal`; no editar migraciones aplicadas; no versionar secretos (el snapshot no contiene datos de personas ni de movimientos).

### Riesgos identificados
- Los UUID de categorías y clasificaciones difieren por empresa: el snapshot debe usar claves naturales (código de cuenta, nombre, dirección) y remapear al aplicar.
- Habilitar Contabilidad exige precondiciones y abre cobertura: el orden de siembra importa.
- Cambiar los módulos por defecto altera el comportamiento de todo alta nueva (decisión ya aprobada).

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — toca el alta de empresa y 6 módulos con una nueva frontera (puerto de defaults) y datos con UUID entre módulos.

### Diseño requerido
**NO** — solo backend y un comando; sin pantallas.

## Diseño
No aplica.

## Arquitectura
`docs/adr/ADR-configuracion-contable-por-defecto-nueva-empresa-snapshot-y-puerto.md`

## Plan
`docs/plans/PLAN-2026-11-19-configuracion-contable-por-defecto-nueva-empresa.md` (v1, COMPLETO) — Specification readiness: READY.

## Implementación
**Resumen.** Puerto `shared/company_defaults` (registro de secciones + `export_all`/`apply_all` atómico, `dry_run`), snapshot `shared/company_defaults/snapshot.json` generado desde «demo dore» (claves naturales, sin UUID), una sección por módulo en `<módulo>/infrastructure/defaults.py` registrada desde su `apps.py`, llamada en `register_company_admin` (misma transacción) y comandos `copy_company_defaults` / `export_company_defaults` en `accounts`.

**Cobertura.** AC-01..05 y AC-09 → `RegisterSeedsDefaultsTests`; AC-06 → aislamiento entre dos altas y empresa anterior intacta; AC-07 → `CopyCommandTests` (vacía, parcial, idempotente, dry-run, empresa inexistente); AC-08 → snapshot sin UUID e ida y vuelta export→apply→export; INV-02/03 → idempotencia y «no pisa» (cuenta 1102 y ajuste existentes); referencia rota → no escribe nada.

**Desviaciones respecto al plan.**
- El `ctx` de la ADR se mantiene pero Contabilidad aporta dos secciones (`accounting` y `accounting_posting`) porque las cuentas por categoría dependen de Gastos y los módulos no pueden importarse entre sí (los tests de frontera lo exigen). Documentado en la ADR.
- El ajuste de Compras se completa solo si está vacío (no pisa una clasificación ya elegida).
- El snapshot no incluye `account_class_settings` (demo dore no tiene filas = todas habilitadas).

**Deuda / notas.** Cada configuración nueva por empresa debe sumar su sección y regenerar el snapshot. La corrida de `export_company_defaults` leyó `doredb` solo en lectura. Sin migraciones ni dependencias nuevas.

**Verificación propia (no es el Quality Gate).** `manage.py test` de accounts, modularity, accounting, expenses, purchases e inventory: 1300 tests OK y suite completa 2277 tests OK; ruff y flake8 sin avisos en los archivos cambiados.

## Review
**PASS** (Quality Gate en subagente aislado, 2026-11-19). Tests de 7 apps: 1681 OK (el autor corrió además la suite completa: 2277 OK); ruff y flake8 sin avisos; bandit sin Medium/High (1 Low falso positivo en un test); límites DDD verificados; AC-01..09 e INV-01..05 con verificación. Revisión visual: no aplica (sin UI). Hallazgos no bloqueantes: REV-2026-11-19-configuracion-contable-por-defecto-nueva-empresa-01 a -04 (docs/reviews/).

## Publicación
PR #109 listo para aprobación humana contra `accounting`; nunca se mergea desde el flujo. Cambio sensible: base de datos / alta de empresa (ADR respaldatorio: ADR-configuracion-contable-por-defecto-nueva-empresa-snapshot-y-puerto). Sin migraciones ni dependencias nuevas.
