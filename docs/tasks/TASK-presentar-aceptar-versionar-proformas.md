# TASK-presentar-aceptar-versionar-proformas: PB-COT-002

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-presentar-aceptar-versionar-proformas (basada en `origin/task/TASK-crear-proformas-de-servicios`, 672d71b, que contiene los PR #52 y #56; por indicación del usuario)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/59
**Fuente:** https://trello.com/c/FF97zg6h/6-pb-cot-002-presentar-aceptar-y-versionar-proformas

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado desde tarjeta Trello | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN | Pantallas modificadas, flujo de varios pasos | delivery-start |
| 2026-11-04 | DESIGN → ARCHITECTURE | Cambia el modelo de datos de dos módulos y el contrato API | delivery-start |
| 2026-11-04 | ARCHITECTURE → PLANNING | ADR y DDR escritos | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | PLAN v1 READY | delivery-start |
| 2026-11-04 | ENGINEERING → REVIEW | Implementación completa; pruebas de API con PostgreSQL pendientes de entorno | delivery-build |

## Investigación

### Requerimiento
[PB-COT-002 · Presentar, aceptar y versionar proformas](https://trello.com/c/FF97zg6h/6-pb-cot-002-presentar-aceptar-y-versionar-proformas) (lista «In Progress», orden 07 de 16, P1; sin etiquetas, checklists ni comentarios). **Insumo funcional, no Specification aprobada por el usuario.** Aclaraciones del usuario: PB-COT-001 vive en los PR #52 (módulo genérico `quotations`) y #56 (módulo `dentistry`, proformas del paciente odontológico) y **la funcionalidad se implementa en ambos módulos**.

Resumen fiel de la tarjeta:
- Historia: como operador, registrar qué tratamientos acepta o rechaza el paciente para autorizar solo el trabajo acordado y conservar la propuesta original.
- Dependencia obligatoria PB-COT-001. Aceptación **por tratamiento** (línea); no depende de Agenda ni de ejecución. Un consultorio por empresa; sin Sucursales ni reserva de recursos.
- Vistas: Cotizaciones → Proformas → Detalle con propuesta, aceptación por tratamiento e historial de versiones; vista imprimible/descargable de la versión presentada, respetando permisos.
- Campos por línea: pendiente/aceptada/rechazada, fecha de decisión, usuario que registra, nombre de quien acepta, medio de aceptación y referencia/evidencia opcional; motivo opcional de rechazo. Totales propuesto, aceptado y pendiente de decisión; versión y vínculo a la anterior.
- Reglas: presentar congela líneas/precios; seleccionar una o varias líneas y registrar aceptación/rechazo explícito (el silencio no es aceptación); confirmar resumen de tratamientos e importe; se acepta la línea completa (dividir una cantidad exige nueva versión); estado derivado pendiente / parcialmente aceptada / aceptada / rechazada; una decisión no se sobrescribe, las rectificaciones se documentan con autor y motivo y no afectan ejecución/cobros vinculados; una nueva versión no duplica líneas ya aceptadas (vínculo de origen, adicionales o reemplazos); nada se ejecuta ni cobra automáticamente.
- Interfaz: cada línea muestra decisión y fecha con texto; el resumen indica exactamente qué acepta el paciente; total aceptado aparte del propuesto y del saldo financiero; versiones anteriores en lectura; imprimir solo datos comerciales autorizados.
- Criterios: proforma 100+200, aceptar la primera y rechazar la segunda → aceptado 100, propuesto 300 y habilita solo la primera; reintentar la confirmación no duplica aceptación ni obligación; nuevas versiones conservan decisiones e historial y no vuelven a facturar el mismo compromiso.
- Transversales: módulos habilitados, empresa de sesión y permisos en interfaz/API; reutilizar componentes; cargando/vacío/error/éxito; conservar datos ante fallos; impedir doble envío; teclado; confirmar acciones irreversibles; el backend es la autoridad.
- El documento de historias de Google Docs enlazado no se leyó (no es accesible desde aquí); el análisis se apoya en la tarjeta, el código y los documentos del repositorio.

### Hechos encontrados
- `git`: `origin/main` (72e6d27) **no contiene** `quotations` ni las proformas de `dentistry`; los PR #52 y #56 se fusionaron en ramas apiladas. La tip de `origin/task/TASK-crear-proformas-de-servicios` (672d71b) los contiene a ambos y está 22 commits por delante y 15 por detrás de `main` (el ancestro común es el merge del PR #50). Se trabaja sobre esa rama y el PR se abre contra ella.
- `backend/modules/quotations/domain/proforma.py:8,64-131` — agregado `Proforma` con estados `draft → presented → superseded`, `present()`, `supersede()`, `new_version()` (copia las líneas con id nuevo, sin vínculo de origen); `ProformaLine` inmutable con `description`, `quantity`, `unit_price`, `treatment_item_id` (reservado) y `piece`.
- `backend/modules/quotations/application/proformas.py:34-145` — `ProformaService`: `present` supersede las presentadas de versión menor (`:78-86`), `new_version` exige que no haya otro borrador (`:88-95`), `allowed_actions` (`:46-51`), `_lines` rehúsa releer el catálogo de líneas ya congeladas (`:122-129`).
- `backend/modules/quotations/infrastructure/django/models.py:6-62` — `ProformaModel` con columna reservada `accepted_total` (nula, sin uso; `:18-19`), `ProformaLineModel`, `ProformaCounterModel`; `repositories.py:60-78` guarda una proforma borrando y recreando todas sus líneas (`ProformaLineModel.objects.filter(...).delete()` + `bulk_create`), lo que **perdería** decisiones e historial si se conservaran en las líneas.
- `backend/modules/quotations/api/views.py:89-134`, `urls.py` — `/api/quotations/proformas/` (lista, detalle, `present/`, `new-version/`), `_run` traduce `ProformaStateError` a 409 y `PriceEditNotAllowed` a 403; `required_modules = ('quotations',)`; política `can_edit_price` por rol en `views.py:29-34`.
- `backend/modules/dentistry/domain/proforma.py:84-150` y `application/proformas.py`, `api/proforma_views.py`, `api/urls.py:12-14` — `DentalProforma` es copia adaptada (pieza dental por línea, `patient_name`, número `ODO-`); API bajo `/api/dentistry/proformas/<id>/…` con `CompanyClinicalPermission` y `required_modules = ('dentistry','customers','services')`; el paciente sale de la URL.
- `docs/adr/ADR-proformas-odontologicas-con-pieza-dental-agregado-propio-en-odontologia.md` — decisión vigente del usuario: duplicación consciente entre `quotations` y `dentistry`; extraer a `shared/` quedó como mejora futura. `docs/architecture/ddd.md:825-840` — `shared` no debe alojar lógica de negocio genérica.
- `backend/modules/sales/tests/test_boundaries.py:13-30` — mapa de dependencias; esta historia no añade dependencias entre módulos.
- Idempotencia: `docs/design/design-system.md:143-146` (formulario con resumen y clave de idempotencia generada al abrir) y `docs/adr/ADR-inventario-movimientos-trazables-registro-idempotente-y-saldo.md` — patrón de clave por operación ya usado.
- Frontend: `frontend/panel_admin/src/app/features/quotations/models/proforma.ts` (tipos, `allowed_actions`), `pages/proforma-detail.component.html:22-52` (muestra «Total aceptado: —» y la tabla de líneas y versiones), `features/dentistry/pages/dental-proforma-detail.component.html`, servicios `proformas-api.service.ts` y `dental-proformas-api.service.ts`; `shared/components` solo tiene `language-selector` y `user-avatar`.
- `frontend/panel_admin/src/app/app.routes.ts:54-77` y `features/dentistry/dentistry.routes.ts:27-29` — rutas de lista/formulario/detalle ya existentes; no hacen falta rutas nuevas salvo la vista imprimible.
- Búsqueda de `accept|decision|aceptad` en ambos módulos: sin implementación previa.

### Hipótesis / supuestos no confirmados
- **Medio de aceptación**: la tarjeta no define el catálogo; se propone cerrado: `in_person`, `phone`, `message`, `email`, `signed_document`, `other`.
- **Rectificación**: se limita al rol con `can_rectify(user)` (hoy admin, único rol existente), solo sobre la versión presentada vigente y solo entre aceptada ↔ rechazada (no vuelve a pendiente).
- **Ejecución/cobros vinculados**: no existen aún; la regla «la rectificación no afecta lo ya vinculado» queda como límite documentado y como punto de extensión para las historias de ejecución y cobro.
- **Descarga**: «imprimible/descargable» se resuelve con vista de impresión del navegador (guardar como PDF), sin dependencias nuevas.
- **Estado derivado**: pendiente = ninguna aceptada y alguna sin decidir; aceptada = todas aceptadas; rechazada = todas rechazadas; parcialmente aceptada = el resto (al menos una aceptada y no todas).
- El nombre de quien acepta es obligatorio al aceptar y opcional al rechazar.

### Módulos y dependencias relacionadas
`quotations` y `dentistry` (cada uno extiende su propio agregado); sin nuevas dependencias entre módulos ni hacia `sales`, `inventory` ni `agenda`.

### Implementaciones similares existentes
Registro con clave de idempotencia y resumen previo (`stock-opening`, recepciones de compras); diálogos `NgbModal` de acción irreversible con motivo; libro append-only de movimientos de inventario.

### Comportamiento actual
Las proformas se crean, presentan (se congelan) y versionan, pero no hay decisiones del paciente, «Total aceptado» es «—» y la nueva versión copia todas las líneas sin vínculo de origen.

### Restricciones
`CLAUDE.md`: `Decimal`; `company_id` en toda consulta; estados por métodos del agregado; no editar migraciones aplicadas; sin dependencias nuevas sin aviso; textos solo por i18n es/en/pt; módulos solo por fachadas; no añadir abstracciones sin necesidad.

### Riesgos identificados
Guardado actual borra y recrea líneas (hay que cambiar a conservar identidad de líneas decididas); duplicación de lógica entre dos módulos; fusión con `main` (15 commits atrás) en `routes.json`, i18n y `test_boundaries.py`; reintentos concurrentes; datos internos filtrados en la vista imprimible; ausencia de ejecución/cobro para probar la regla de rectificación.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el modelo de datos y el contrato de dos módulos, introduce un libro de decisiones inmutable con idempotencia y reglas de dinero y de versionado.

### Diseño requerido
**SI** — el detalle de proforma gana selección múltiple, diálogo de confirmación, historial y vista imprimible.

## Diseño
Ver [DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion](../design/DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion.md).

## Arquitectura
Ver [ADR-presentar-aceptar-versionar-proformas-libro-de-decisiones-y-versionado](../adr/ADR-presentar-aceptar-versionar-proformas-libro-de-decisiones-y-versionado.md).

## Plan
[PLAN-2026-11-04-presentar-aceptar-versionar-proformas](../plans/PLAN-2026-11-04-presentar-aceptar-versionar-proformas.md) v1 · COMPLETO · Specification readiness: READY (supuestos no bloqueantes listados arriba y en el plan).

## Implementación
Backend (copia adaptada en `quotations` y `dentistry`): agregado con libro de decisiones (`Decision`), `decide`/`rectify`, estado derivado y totales, versionado con `origin_line_id`/`line_kind` y recálculo al guardar (INV-01..11); repositorio que guarda por diferencia con ids de línea estables; idempotencia por lote (`…_decision_batch`); API `decisions/`, `lines/<id>/rectify/`, `printable/`; migraciones `quotations/0002` y `dentistry/0003`. Frontend: componente compartido `app-proforma-decisions` (totales, selección, diálogo de dos pasos con resumen, rectificación, historial), `ProformaDecisionsApiService`, página de impresión `ProformaPrintPageComponent`, rutas `…/imprimir`, claves `PROFORMA_DECISIONS.*` en es/en/pt y adaptación de ambos detalles.

Cobertura: INV-01..09, AC-01, 04..09 → `test_decisions_domain.py` y `test_proforma_decisions_domain.py` (SimpleTestCase); AC-01..13 → `test_decisions_api.py` y `test_proforma_decisions_api.py` (TransactionTestCase); AC-14 → specs de `ProformaDecisionsComponent` y `ProformaDecisionsApiService`, `ng build`, `i18n:check`, lint.

Verificación propia (no es el Quality Gate): dominio de ambos módulos 34/34 OK sin base de datos; `makemigrations` genera solo las migraciones aditivas; `test_boundaries` OK; `ng build --configuration development` OK; `ng lint` OK; `i18n:check` 1719 claves, 0 faltantes; specs de `shared`, `quotations` y `dentistry` 80/80 OK. **No ejecutado:** las pruebas de API con PostgreSQL (no hay `DATABASE_URL` en este entorno y no se lee `.env`).

Desviaciones respecto al plan:
- `allowed_actions` no cambia (compatibilidad total de AC-15): las acciones nuevas viajan en `decision_actions` (`decide`, `rectify`).
- DDR: un único componente compartido `app-proforma-decisions` con un solo `<dialog>` nativo (patrón ya usado por los detalles) en lugar de tres componentes con `NgbModal`; el historial va dentro del mismo componente.
- La clave de idempotencia se genera al abrir el diálogo y se reutiliza en cada reintento (patrón de `stock-opening`).

Deuda técnica: lógica de decisiones duplicada en dos módulos (decisión del ADR); la protección de rectificaciones frente a ejecución/cobros vinculados queda como límite hasta que existan esas historias; la vista de impresión usa el diálogo del navegador. Pantallas de referencia: Detalle con acciones de ciclo de vida (`purchase-detail`) y formulario con resumen (`stock-opening`).

## Review
Quality Gate 1 (ejecutado por el mismo agente porque no se lanzó subagente; aislamiento procedimental): **NO CONCLUYE (sin PASS)**. Sin hallazgos Critical/High, pero una verificación aplicable no se pudo ejecutar.
Ejecutado y OK: dominio de `quotations` y `dentistry` + `test_boundaries` (46 pruebas), `makemigrations --check`, `ng build`, `ng lint`, `npm run i18n:check` (0 faltantes), `npm audit` (0 vulnerabilidades), specs de `shared`/`quotations`/`dentistry` (80/80). Suite completa de frontend: 1238 OK y 1 fallo preexistente fuera del alcance ([REV-02](../reviews/REV-2026-11-04-presentar-aceptar-versionar-proformas-02.md), Low).
**No ejecutado:** pruebas de API con PostgreSQL ([REV-01](../reviews/REV-2026-11-04-presentar-aceptar-versionar-proformas-01.md), Medium), `bandit`/`ruff` (no instalados), revisión visual en navegador (requiere backend y base de datos).
Para el PASS: correr `python manage.py test modules.quotations modules.dentistry modules.modularity modules.service_catalog modules.sales.tests.test_boundaries` con PostgreSQL y la revisión visual; luego repetir el gate.

## Publicación
_Pendiente_
