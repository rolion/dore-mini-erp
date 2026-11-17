# TASK-configurar-asientos-automaticos-modulo: Configuración simple de asientos automáticos por módulo (CONT-12)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configurar-asientos-automaticos-modulo
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/86
**Fuente:** https://trello.com/c/SoDkSaoU/15-cont-12-definir-configuraci%C3%B3n-simple-de-asientos-autom%C3%A1ticos-por-m%C3%B3dulo

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado; base = rama `accounting` (`origin/accounting`, PR #84 integrado), no `main` | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN → ARCHITECTURE → PLANNING | NEEDS_ARCHITECTURE (tabla nueva, contrato de fachada usado por 5 módulos), diseño SI; 1 decisión de alcance resuelta por la persona | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY; PLAN v1 | delivery-start |
| 2026-11-16 | ENGINEERING → REVIEW | Implementación completa según PLAN v1; pruebas propias en verde | delivery-build |
| 2026-11-16 | REVIEW (1.ª pasada) | Quality Gate PASS (0 Critical/High; REV-01 Medium, REV-02..05 Low abiertos) | delivery-publish |
| 2026-11-16 | REVIEW (corrección) | REV-01..04 corregidos; REV-05 (Specification) abierto a la espera de aprobación; se repite el Quality Gate | delivery-publish |
| 2026-11-16 | REVIEW → PUBLISH | 2.ª pasada del Quality Gate PASS; REV-06..08 (cambios de estilo y una línea de prueba) corregidos sin repetir el Gate; REV-05 abierto | delivery-publish |

## Investigación

### Requerimiento
Tarjeta Trello CONT-12 (insumo, no Specification aprobada). Aclaración de la persona: usar la rama `accounting` como base.
- **Objetivo:** configurar cuentas por evento de negocio sin exponer un constructor genérico de reglas.
- Contrato común de selección de cuentas con **vista previa Debe/Haber**; cada módulo muestra solo los eventos que utiliza.
- Métodos de pago (efectivo, transferencia…) → cuentas **Caja/Banco de Activo**; el método de pago no es una cuenta.
- Ventas/Servicios: ingresos y cuentas por cobrar. Inventario: inventario y costo de ventas. Compras: inventario y proveedores (cuentas por pagar). Gastos: cuenta de gasto por categoría y cuenta de pago.
- Validar empresa, cuenta habilitada y clasificación por rol. Mostrar la configuración faltante **antes** de confirmar; con módulo habilitado no se omite la contabilización en silencio.
- Cambiar la configuración afecta solo operaciones futuras; la reversión usa las cuentas originales.
- Con Contabilidad deshabilitada, los módulos siguen independientes; reactivar no contabiliza históricos. Proteger correcciones de operaciones ya contabilizadas.
- Guardar origen inequívoco y deduplicar cada evento con el motor CONT-02.
- Aceptación: (1) cambiar Banco por Caja no modifica un asiento histórico; (2) configuración incompleta o cuenta deshabilitada impide la operación integrada con mensaje accionable; (3) deshabilitar Contabilidad no exige cuentas ni genera asientos al reactivar; (4) cuenta ajena o clasificación inválida se rechaza en API.
- Dependencias: CONT-02 (motor), CONT-09 (cuentas), CONT-10 (períodos) — hechas en `accounting`. Transversal: API y UI, aislamiento por empresa, permisos existentes, `Decimal` y moneda existentes, sin conversión de divisas.
- Aclaración de la persona (2026-11-16): **la configuración vive en cada módulo** (no en Contabilidad); se monta ya en **Ventas, Compras, Inventario y Gastos**.

### Hechos encontrados
- **Ningún módulo contabiliza por partida doble todavía.** `post_journal_entry` solo lo usa la propia API de asientos manuales (`backend/modules/accounting/api/journal_views.py`); Ventas, Cobros, Gastos y Compras solo llaman al contrato anterior `record_entry`/`resolve_account` (`modules/receivables/infrastructure/adapters.py:58-64`, `modules/expenses/infrastructure/adapters.py:25-35`, `modules/purchases/infrastructure/adapters.py:108-118`, `modules/sales/infrastructure/adapters.py:14`). La integración real llega con VEN-01, COM-01/02, INV-01 y las tarjetas de gastos (tablero Trello). CONT-12 define la configuración y el contrato que esas tarjetas consumen.
- Motor: `backend/modules/accounting/services.py:322-362` (`post_journal_entry` idempotente por `(empresa, origen)`; `reverse_journal_entry` usa las cuentas originales aunque estén deshabilitadas, `services.py:365-378`); `JournalEntryInput.origin_kind` ≤ 30 caracteres (`domain/journal.py:15`), conflicto `origin_conflict` y rechazo si el origen ya está en el libro anterior (`domain/journal.py:23-24`, `application/journal.py:86-93`). El vocabulario `origin_kind` de los módulos aún no existe (deuda declarada en `TASK-asientos-manuales-navegacion-contable`).
- Las líneas del asiento guardan `account_id` (`infrastructure/django/models.py:245-265`): un cambio de configuración no puede alterar asientos históricos.
- Cobertura: `coverage_status(company_id, fecha)` (`services.py:127-141`) decide si una operación debe crear movimiento (módulo deshabilitado, anterior al corte o en hueco de cobertura ⇒ no); es la fuente única para AC-3.
- Cuenta: `Account` tiene `account_class` (ASSET/LIABILITY/EQUITY/INCOME/EXPENSE/COST, `domain/account_class.py:7-14`), `kind` Caja/Banco/Billetera solo en Activo (`domain/account.py:127-130`), `is_active`, moneda y código; clases deshabilitables por empresa (`AccountClassSettingModel`, `models.py:39-50`).
- Métodos de pago: `MethodMapping` por empresa (`domain/account.py:157-174`, tabla `accounting_method_mapping`, `models.py:105-119`) con `PUT /api/accounting/payment-methods/<code>/` (`api/views.py:353-360`, `ConfigureMethod`). Hoy acepta **cualquier cuenta activa en BOB**: no exige Activo ni tipo Caja/Banco. Catálogo: `PAYMENT_METHODS` CASH/QR/BANK_TRANSFER/CARD/OTHER (`domain/catalog.py:6-10`). `resolve_account` devuelve el destino de un método (`services.py:64-77`).
- Egresos por categoría: las categorías de gasto son `Classification` de dirección EXPENSE de Contabilidad (`domain/classification.py`, `models.py:85-102`); Gastos y Compras las validan por la fachada (`expenses/infrastructure/adapters.py:25-31`).
- API de Contabilidad: rutas en `api/urls.py:30-62`; `_ConfigView` y `_run` convierten errores de dominio (`api/views.py:95-125`); las pantallas de cuentas/clasificaciones no exigen Contabilidad habilitada («la empresa configura sus cuentas antes de habilitar», `app.routes.ts:104`).
- Frontend: configuración por módulo en `features/settings/pages/module-settings` con `data.settingsModule` para `sales`, `purchases`, `inventory` (`app.routes.ts:203-209, 243-249, 342-348`), con pestañas «General» e «Historial de cambios» (`module-settings.component.ts:37`); `inventory/configuration` para almacenes/unidades (`app.routes.ts:298`). **Gastos no tiene pantalla de configuración** (rutas en `features/expenses/expenses.routes.ts`: lista, categorías, detalle, formulario). Servicios aceptados en el motor serán de `receivables`/`quotations` (módulos `receivables`, `quotations`, `services`, `modules/modularity/domain/modules.py:18-26`).
- Migraciones de Contabilidad: la última es `0010_journal_entry.py`; la tabla nueva será `0011` (solo `CreateModel`).
- Plantillas de diseño: «Configuración con listados en pestañas y diálogo» y «Variante de operación con previsualización obligatoria» (`docs/design/design-system.md` §5); `AccountsTabComponent`/`MethodsTab` existentes como referencia de selección de cuenta.

### Hipótesis / supuestos no confirmados
- Una sola cuenta por rol y empresa (p. ej. una «Cuentas por cobrar» para Ventas y Servicios, una «Inventario» compartida por Compras e Inventario); es lo habitual y lo que la tarjeta describe («inventario y proveedores»). Si una empresa necesitara separar CxC de ventas y de servicios, es una ampliación del catálogo, sin migración.
- El **método de pago → cuenta Caja/Banco** es **un solo mapeo por empresa** (el existente `MethodMapping`), compartido por cobros de ventas, pagos de compras y gastos, no uno por módulo: una caja es la caja de la empresa. Ventas, Compras y Gastos lo muestran y editan sobre el mismo dato.
- «Cuenta habilitada» = activa, de la empresa y con su clasificación contable habilitada; «clasificación adecuada por rol» sale del catálogo (ver Decisiones).
- Un módulo puede contabilizar un evento por el helper de esta tarea (`post_automatic_entry`) o por `post_journal_entry` con el `origin_kind` del catálogo; migrar cada módulo es de VEN/COM/INV/GAS, no de esta tarea.

### Decisiones resueltas
1. **Dónde vive la UI (persona, 2026-11-16):** en cada módulo, no en Contabilidad. Se monta en Ventas, Compras, Inventario y Gastos (esta última con una sección de configuración nueva). Cobros/Servicios queda en el catálogo del backend pero sin pantalla propia en esta tarea (su host lo definen VEN-01/servicios).
2. Resto por criterio, documentado en ADR/PLAN: catálogo de eventos y roles fijo en código; mapeo único por rol y empresa; método → cuenta reutiliza `MethodMapping` endureciendo la validación de **usos nuevos**.

### Módulos y dependencias relacionadas
`accounting` (catálogo, persistencia, API, fachada) y su frontend; `sales`, `purchases`, `inventory`, `expenses` (frontend: solo montan el panel; sin cambios de backend ni dependencia nueva hacia `accounting` en backend). Sin paquetes nuevos.

### Implementaciones similares existentes
`ConfigureMethod` + `MethodListView` (mapeo método → cuenta) y la pantalla «Métodos de pago»; configuración por módulo y empresa (`ADR-configuracion-por-modulo-y-empresa-modelo-y-contrato`); motor `post_journal_entry` y cobertura `coverage_status`.

### Comportamiento actual
Existe el motor y el mapeo método → cuenta (sin validar clasificación). No hay mapeo de cuentas por evento ni forma de saber, antes de operar, si falta configuración. Los módulos no generan asientos.

### Restricciones
`CLAUDE.md`: `Decimal`, aislamiento por `company_id` (empresa del usuario, nunca del cliente), dominio sin Django, módulos de negocio no importan `accounts` ni infraestructura ajena (solo la fachada `accounting.services`), sin texto visible hardcodeado (claves es/en/pt, `tr()`), sin `any`, Reactive Forms, nunca editar una migración aplicada. Sin conversión de divisas: moneda de los flujos BOB.

### Riesgos identificados
- Endurecer el mapeo de métodos (Activo + Caja/Banco/Billetera) puede dejar sin poder reasignar a empresas con cuentas heredadas sin clasificar → solo valida usos nuevos; la configuración existente sigue resolviendo; mensaje accionable apunta a clasificar la cuenta.
- Una cuenta configurada que luego se desactiva o reclasifica → la resolución lo detecta en cada evento y bloquea con mensaje accionable (no contabiliza mal en silencio).
- Que los módulos migren con un `origin_kind` distinto del catálogo → el catálogo es la única fuente y `post_automatic_entry` solo acepta códigos del catálogo.
- Coherencia con la deuda de `design-system.md` (alerta tenue, contraste AA): usar los patrones vigentes.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — tabla y migración nuevas, contrato de fachada que consumirán cinco módulos y política de validación de cuentas por rol (reglas de dinero/permisos); un ADR fija el catálogo, el modelo y la fachada.

### Diseño requerido
**SI** — pantalla nueva de configuración con vista previa Debe/Haber montada en cuatro módulos, con estados y mensajes accionables.

## Diseño
`docs/design/DDR-configurar-asientos-automaticos-modulo-panel-cuentas-por-evento.md`

## Arquitectura
`docs/adr/ADR-configurar-asientos-automaticos-modulo-catalogo-modelo-y-fachada.md`

## Plan
`docs/plans/PLAN-2026-11-16-configurar-asientos-automaticos-modulo.md` (v1, COMPLETO) · Specification readiness: READY

## Implementación
Implementado según PLAN v1, sin cambios de Specification. La rama se actualizó con `origin/accounting` (PR #85) durante el trabajo; sin conflictos.

- **Dominio** (`accounting/domain/posting.py`; INV-01/02, AC-01/03): catálogo fijo de 8 roles y 8 eventos (código = `origin_kind`), `account_problem`/`validate_account_for_role` (empresa, activa, BOB, con código y clasificación, clasificación habilitada, tipo Caja/Banco/Billetera para dinero), `PostingIssue` con mensaje que nombra el módulo donde corregir, `PostingConfigurationMissing`.
- **Casos de uso** (`application/posting.py`; AC-02/06/07): `DescribePostingConfig` (vista previa Debe/Haber, faltantes por todos los métodos y categorías activos, roles compartidos), `SetRoleAccount`, `SetCategoryAccount`, `resolve_event` (en vivo, sin caché).
- **Persistencia** (AC-10): `PostingAccountModel` + migración `0011_posting_account` (solo `CreateModel`) + `DjangoPostingConfigRepository` (todo por `company_id`).
- **Fachada** (`services.py`; AC-05..AC-09): `describe_posting_config`, `set_role_account`, `set_category_account`, `check_posting_ready` (sin cobertura `required=False`), `post_automatic_entry` (cobertura → resolución → `post_journal_entry` con `origin_kind` = evento; nunca omite en silencio), `reverse_automatic_entry` (cuentas originales; `None` si nunca se contabilizó).
- **API** (API-01..03; AC-01..04, AC-11): `GET posting-config/?module=`, `PUT posting-config/roles/<role>/`, `PUT posting-config/categories/<id>/`; sin `required_modules` (se configura antes de habilitar Contabilidad). **API-04:** `ConfigureMethod` valida un uso nuevo y activo del método (Activo con tipo Caja/Banco/Billetera, con código y clasificación); lo ya configurado no se revalida.
- **Frontend** (AC-12..AC-14): `PostingConfigPanelComponent` (Reactive Forms por fila, vista previa en vivo, estados), `PostingConfigApiService`, modelos; pestaña «Asientos automáticos» en `module-settings` (Ventas, Compras, Inventario); página y ruta `/expenses/settings` + ítem de menú «Configuración» en Gastos; i18n es/en/pt (`ACCOUNTING.POSTING.*`); `design-system.md` §5/§6 actualizado.
- **Pantallas de referencia:** «Configuración con listados en pestañas y diálogo» (`methods-tab`, `inventory-configuration`) y «Variante de operación con previsualización obligatoria» (`regularization`); componentes reutilizados: tablas `inventory-table`, `alert` tenue, `RouterLink` a Cuentas. Componente nuevo reutilizable: `app-posting-config-panel` (anotado en `design-system.md`).

**Desviaciones respecto al plan:**
0. **PLAN v2 (2026-11-17, a pedido de la persona):** el mapeo de métodos de pago ya no exige tipo de cuenta Caja/Banco/Billetera; basta Activo, BOB, activa y con código. Backend, panel (filtro del selector, textos es/en/pt) y pruebas ajustados.
1. El endurecimiento del mapeo método→cuenta (API-04) obligó a corregir las cuentas de prueba de `sales`, `receivables` y `accounting` (ahora `money_account` en `tests/journal_support.py`: Activo, con código y tipo Caja/Banco). Es el efecto previsto del riesgo «endurecer método→cuenta» del PLAN.
2. La validación del método se aplica solo cuando se asigna una cuenta nueva **y el método queda activo** (asignar una cuenta a un método inactivo sigue permitido, como antes).
3. El panel no usa `ng-select` (select nativo, como el resto de Contabilidad), de acuerdo con el DDR.

**Deuda técnica / pendiente:** los módulos aún no llaman a `check_posting_ready`/`post_automatic_entry` (VEN-01, COM-01/02, INV-01 y gastos); Cobros/Servicios no tiene pantalla de configuración (su catálogo existe en backend); no hay historial de cambios de configuración (fuera de alcance). Revisión visual en navegador pendiente para `delivery-publish`.

**Pruebas añadidas (corridas propias, no son el Quality Gate):** backend `test_posting_domain` (3), `test_posting_service` (28), `test_posting_config_api` (9); suite completa del backend 1959 OK, `makemigrations --check` sin cambios; frontend `posting-config-api.service.spec`, `posting-config-panel.component.spec` (14), `expense-settings`, `module-settings` y `sidebar-menu` actualizados; suite completa 1570 OK, `ng lint` OK, `i18n:check` 0 faltantes, `ng build` OK.

## Review
**Quality Gate 1.ª pasada: PASS** (subagente aislado, 2026-11-16). Backend: `manage.py test` 1959 OK, `makemigrations --check` sin cambios, flake8 con avisos E501 nuevos (corregidos), bandit B101 Low (corregido). Frontend: lint OK, `i18n:check` 2174 claves y 0 faltantes, `ng build` OK, suite completa 1570 OK. Revisión visual parcial: Gastos (escritorio 1024 px, claro, guardado persistente) y Ventas (375 px, tema oscuro emulado); Compras e Inventario solo por specs.
- REV-01 (Medium, IMPLEMENTATION; **resuelto**): el reintento idempotente de `post_automatic_entry` fallaba si la configuración había cambiado.
- REV-02 (Low, IMPLEMENTATION; **resuelto**): faltaban pruebas de AC-08 (hueco) y AC-11 (403/401).
- REV-03 (Low, DESIGN; **resuelto**, pendiente de confirmar en navegador): recorte de la vista previa y bordes sueltos a 375 px.
- REV-04 (Low, IMPLEMENTATION; **resuelto**): E501 y `assert` en código nuevo.
- REV-05 (Low, SPECIFICATION; **abierto**): la forma real de API-01 difiere de la documentada (`issues` trae `subject`/`module`, `preview` trae `role` y `account{}`), y los mensajes de faltantes vienen del backend solo en español. Requiere aprobación para actualizar la Specification (PLAN v2).

## Review (segunda pasada)
**Quality Gate: PASS** (subagente aislado, 2026-11-16, tras corregir REV-01..04). Backend: `manage.py test` 1962 OK, `makemigrations --check` sin cambios, bandit sin hallazgos, flake8 solo con avisos preexistentes más un E303 (REV-08). Frontend: lint OK, `i18n:check` 2174 claves y 0 faltantes, `ng build` OK, suite completa 1570 OK. REV-01..04 comprobados contra el código y resueltos; AC-08, AC-09 y AC-11 pasan a cumplidos.
- **Revisión visual** (navegador integrado, 375 px y escritorio 1440 px, tema claro; tema oscuro solo a 375 px en Ventas, emulado con clases del `body`): sin recorte ni desborde horizontal a 375 px.
- REV-06 (Low, DESIGN; **resuelto**): barra vertical interna en la vista previa.
- REV-07 (Medium, DESIGN; **resuelto**): contraste 2,18:1 de `text-warning-emphasis` en tema oscuro (estados «Sin configurar» y faltantes).
- REV-08 (Low; **resuelto**): línea en blanco sobrante (E303) en una prueba.
- REV-05 (Low, SPECIFICATION; **abierto**): forma real de API-01 distinta de la Specification y mensajes de faltantes solo en español; requiere aprobación para PLAN v2.
- **Sin repetir el Quality Gate:** REV-06, 07 y 08 se corrigieron después de la 2.ª pasada (CSS y una línea de prueba, sin lógica). Tras el cambio se volvió a pasar lint, build y la suite del frontend (1570 OK); **no se volvió a medir el contraste en el navegador ni en el conmutador real de tema oscuro**.

## Publicación
PR https://github.com/rolion/dore-mini-erp/pull/86 (base `accounting`) listo para aprobación humana; no se mergea. Incluye ADR (modelo de datos nuevo, migración `0011`): lo aprueba una persona. Pendiente de aprobación: REV-05 (cambio de Specification).
