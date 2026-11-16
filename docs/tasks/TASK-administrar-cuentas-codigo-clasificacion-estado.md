# TASK-administrar-cuentas-codigo-clasificacion-estado: Administrar cuentas con código, nombre, clasificación y estado (CONT-09)

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-administrar-cuentas-codigo-clasificacion-estado (base: `task/TASK-configurar-seis-clasificaciones-contables`, PR #79 de CONT-08 aún sin mergear)
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/80
**Fuente:** https://trello.com/c/6XUugVjJ

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-16 | (nuevo) → INVESTIGATION | Task creado desde la tarjeta CONT-09 | delivery-start |
| 2026-11-16 | INVESTIGATION → DESIGN | Cambia la pantalla de cuentas | delivery-start |
| 2026-11-16 | DESIGN → ARCHITECTURE | Cambia el contrato de la cuenta (código, clasificación obligatoria, tipo de dinero opcional) | delivery-start |
| 2026-11-16 | ARCHITECTURE → PLANNING | DDR y ADR escritos | delivery-start |
| 2026-11-16 | PLANNING → ENGINEERING | Specification READY | delivery-start |
| 2026-11-16 | ENGINEERING → REVIEW | Implementación completa | delivery-build |
| 2026-11-16 | REVIEW → PUBLISH | Quality Gate PASS (REV-01 Medium, REV-02 y REV-03 Low abiertos, no bloqueantes) | delivery-publish |
| 2026-11-16 | PUBLISH (sin cambio) | REV-01 corregido; re-revisión PASS; REV-01 cerrado | delivery-build / delivery-publish |
| 2026-11-16 | PUBLISH (sin cambio) | Quality Gate repetido sobre el estado actual con el código numérico (PLAN v3): PASS | delivery-publish |
| 2026-11-16 | PUBLISH (sin cambio) | REV-02..05 corregidos (PLAN v4); re-revisión independiente pendiente | delivery-build |

## Investigación

### Requerimiento
Fuente: tarjeta Trello CONT-09 (insumo, no Specification aprobada). Depende de CONT-08. Base de trabajo: rama `accounting`; no se mergea a `main`.
- Unificar el plan de cuentas en el submenú Cuentas: listar, agregar, editar y habilitar/deshabilitar; código y nombre obligatorios, clasificación obligatoria; código único por empresa.
- Al crear una cuenta, ofrecer solo clasificaciones habilitadas.
- Impedir cambiar la clasificación de una cuenta con asientos confirmados; permitir renombrar sin alterar históricos; no ofrecer borrado.
- Las cuentas deshabilitadas siguen en consultas y saldos, pero no en nuevos asientos ni configuraciones.
- Si se deshabilita una cuenta usada por una configuración automática, mostrar su impacto; la operación posterior debe pedir corregir la configuración, sin sustituciones silenciosas.
- Aceptación: (1) crear Caja/101/Activo; rechazar código repetido en la misma empresa y permitirlo en otra; (2) deshabilitar Caja la oculta en formularios nuevos y mantiene historial y saldos; (3) rechazar cambio de clasificación de una cuenta utilizada y aceptar el cambio de nombre.

Aclaraciones del dueño (2026-11-16):
- El plan de cuentas que se cargará después (**no se carga en esta tarea**) tiene 40 cuentas con código jerárquico `1.1.01 … 6.2.02`, nombre y una de las seis clasificaciones.
- «Depreciación acumulada» (1.2.05) es de Activo pero **cuenta correctora** (saldo acreedor); el diseño decide cómo marcarla.
- Solo algunas cuentas de Activo son de dinero (Caja 1.1.01, Bancos 1.1.02); hoy el tipo Caja/Banco/Billetera es obligatorio y no aplica al resto.
- Decisión sobre deshabilitar una cuenta usada por métodos de pago: **seguir bloqueando** con el 409 actual que lista los métodos afectados (respuesta del dueño a la pregunta de la tarjeta).

### Hechos encontrados
- `backend/modules/accounting/domain/account.py:78-105` — `Account` tiene `name`, `currency`, `kind` (nulable), `account_class` (nulable, CONT-08) y `opening_balance`; **no tiene código**. `Account.create` valida el nombre y la moneda; `kind` no es obligatorio en el dominio.
- `backend/modules/accounting/api/serializers.py:16-28` — el serializer de alta exige `kind`; es el único lugar donde es obligatorio hoy (`AccountInputSerializer`).
- `backend/modules/accounting/application/use_cases.py:62-123` — `UpdateAccount` ya bloquea cambiar moneda y apertura si hay entradas (`account_has_entries`, `use_cases.py:90,102`) usando `has_entries_for_account` (`infrastructure/django/repositories.py:317`); es el patrón para bloquear la clasificación. `DeactivateAccount` (`use_cases.py:125-140`) responde 409 `account_in_use` con los métodos afectados.
- `backend/modules/accounting/infrastructure/django/models.py:8-30` — único `(lower(name), company_id)`; `account_class` y la tabla `accounting_account_class_setting` llegan en `0007` (CONT-08).
- `backend/modules/accounting/services.py:63-75` — `validate_money_account` rechaza cuentas inexistentes o inactivas para usos nuevos; `resolve_account` (`services.py:42`) usa `can_receive` (activa y en BOB).
- `frontend/panel_admin/src/app/features/accounting/components/accounts-tab/accounts-tab.component.html:37-44` — la tabla muestra Nombre, Tipo, Moneda, Apertura, Estado y Acciones; el diálogo (`account-dialog`) exige tipo y ofrece clasificación opcional (CONT-08).
- La base local quedó vacía de cuentas (limpieza del 2026-11-16): no hay datos que migrar localmente. Producción puede tener cuentas anteriores (sin tipo, sin clasificación, sin código).
- `docs/adr/ADR-configurar-seis-clasificaciones-contables-catalogo-fijo-y-validacion.md` — decisión 4: código y obligatoriedad quedan para CONT-09, sin reabrir el contrato.

### Hipótesis / supuestos no confirmados
- «Asientos confirmados» equivale hoy a las entradas del libro de una sola cuenta (`accounting_entry`); cuando CONT-02 introduzca asientos con líneas, la comprobación se apoyará en las líneas de la cuenta.
- ~~El código admitía letras, dígitos, punto, guion y guion bajo.~~ **Actualizado (2026-11-16, decisión del dueño):** el formato es libre para cada empresa y por ahora solo numérico (p. ej. `111001`, hasta 20 dígitos); es único dentro de la empresa y otra empresa puede repetirlo.

### Módulos y dependencias relacionadas
`accounting` (dueño). Los módulos que crean cobros/pagos consumen la fachada (`resolve_account`, `validate_money_account`), que no cambia.

### Implementaciones similares existentes
`UpdateAccount` (bloqueos por entradas), `AccountConflict`, el diálogo `account-dialog` y la pestaña `accounts-tab` (plantilla de configuración con listados).

### Comportamiento actual
Las cuentas son destinos de cobros y pagos: nombre, moneda, tipo Caja/Banco/Billetera obligatorio, sin código; la clasificación contable es opcional (CONT-08).

### Restricciones
`CLAUDE.md`: aislamiento por `company_id`, no editar migraciones aplicadas, dominio sin Django, sin texto hardcodeado en el frontend (es/en/pt), sin `float`. Tarjeta: sin borrado de cuentas; sin sustituciones silenciosas. Decisión del dueño: sin cargar el plan de cuentas aquí.

### Riesgos identificados
- Alta de cuenta: pasa a exigir código y clasificación (cambio de contrato; el único cliente es el panel, que se actualiza en el mismo PR).
- Cuentas anteriores sin código ni clasificación: siguen operando; se completan al editarlas.
- Con un plan completo, el selector de destino de los métodos de pago listará también cuentas que no son de dinero: lo resuelve CONT-12 (mapeo a Caja/Banco), fuera de esta tarea.
- El bloqueo por «asientos confirmados» usa entradas de una sola cuenta hasta CONT-02.

### Veredicto de complejidad
**NEEDS_ARCHITECTURE** — cambia el modelo de la cuenta (migración), el contrato del API y las reglas de dominio, y lo consumen CONT-02, CONT-04, CONT-11 y CONT-12.

### Diseño requerido
**SI** — cambian la lista y el diálogo de cuentas.

## Diseño
`docs/design/DDR-administrar-cuentas-codigo-clasificacion-estado-lista-y-formulario-de-cuentas.md`.

## Arquitectura
`docs/adr/ADR-administrar-cuentas-codigo-clasificacion-estado-modelo-de-cuenta.md`.

## Plan
`docs/plans/PLAN-2026-11-16-administrar-cuentas-codigo-clasificacion-estado.md` (v3) · Modo: COMPLETO · Specification readiness: READY.

## Implementación
Cuentas del plan con código único por empresa, clasificación obligatoria, tipo de dinero opcional (solo Activo) y marca de cuenta correctora.

- **Dominio** (`domain/account.py`): `validate_code` (INV-01), `code`, `is_contra`, `ensure_consistent` (INV-04).
- **Datos** (migración `0008_account_code_contra`): `code` nulable, `is_contra` y restricción única parcial `(company_id, lower(code))` (INV-02). Aditiva.
- **Casos de uso** (`application/use_cases.py`): `CreateAccount` exige código y clasificación habilitada; `UpdateAccount` bloquea el cambio de clasificación y de `is_contra` con entradas (409 `account_has_entries`, INV-05), permite renombrar y recodificar; `null` en PATCH = sin cambio. `DeactivateAccount` sin cambios (INV-07).
- **Repositorio:** unicidad de código y nombre con errores por campo; las carreras devuelven 400, no 500; listado por código (nulos al final) y filtro por clasificación.
- **API:** `code`, `account_class`, `is_contra`, `kind` opcional (API-01..03).
- **Frontend:** columnas Código y Clasificación, etiqueta «Correctora», «Sin código», filtro por clasificación; diálogo con código, clasificación, tipo de dinero (solo Activo) y casilla correctora; es/en/pt.
- **Cobertura de AC:** AC-01..AC-10 en `test_account_plan.py` y `test_account_classes.py`; AC-11 con la prueba de migración; AC-12 en los specs de lista, diálogo y servicio.

**Desviaciones del plan:**
1. ~~El diálogo no bloqueaba campos por asientos.~~ **Resuelta (REV-02):** el API expone `has_entries` (una consulta por listado) y el diálogo deshabilita la clasificación y la casilla correctora; el 409 del servidor sigue siendo la barrera real.
2. Se actualizaron pruebas existentes (`test_api`, `test_classifications`, `test_coverage`, `test_account_classes` y los specs del frontend) al nuevo contrato de alta (código y clasificación obligatorios, tipo opcional).

**Verificación propia (no es el Quality Gate):** backend completo 1793 OK; `makemigrations --check` sin cambios; frontend `ng test` 1468 OK, `ng lint` limpio, `i18n:check` 0 faltantes, `ng build` correcto.

**UI:** pantalla de referencia `accounts-tab`/`account-dialog` (plantilla de configuración con listados); badges y tabla existentes, sin componentes compartidos nuevos.

**Deuda técnica:** el campo «Tipo» (Caja/Banco/Billetera) se conserva en el formulario por ahora; el dueño decidió quitarlo por completo más adelante (2026-11-16), lo que obligará a decidir cómo CONT-12 elige la cuenta de dinero de cada método de pago; el selector de métodos de pago mostrará también cuentas que no son de dinero hasta CONT-12; el bloqueo por asientos usa entradas de una cuenta hasta CONT-02.

## Review
**Resultado: PASS** (subagente aislado, solo desde artefactos y diff contra la base del PR).
- Backend: suite completa 1793 OK; `makemigrations --check` sin cambios; flake8 solo E501 y un F401 preexistente; mypy solo `import-untyped` (101 líneas sin desglosar); bandit sin hallazgos (sin línea de resumen).
- Frontend: `ng test` 1468 OK; `ng lint` limpio; `i18n:check` 0 faltantes; `ng build` correcto; `npm audit`: 2 moderadas sin relación con el diff.
- AC-01..AC-12, INV-01..07 y API-01..03 con verificación real; DDD y migración aditiva conformes; sin secretos ni artefactos; sin scope creep.
- Hallazgos abiertos, no bloqueantes: [REV-01](../reviews/REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-01.md) (Medium, IMPLEMENTATION: el tipo de dinero no se puede quitar y bloquea reclasificar cuentas anteriores sin mensaje visible), [REV-02](../reviews/REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-02.md) (Low, DESIGN: desviación declarada de UI-02) y [REV-03](../reviews/REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-03.md) (Low: clave i18n sin uso).
- No verificado: revisión visual en navegador; carga con datos reales de producción; interacción con CONT-02, CONT-04 y CONT-12.
- **Re-revisión tras la corrección de REV-01** (commit `6b47154`, subagente aislado): PASS. Backend suite completa 1795 OK; frontend 1471 OK, lint, i18n y build limpios. **REV-01 cerrado.** Quedan abiertos REV-02 y REV-03 (Low). El PLAN pasó a v2 (API-04) con aprobación del usuario.

- **Quality Gate repetido sobre el estado actual** (PLAN v3, código numérico, REV-01 corregido): **PASS**. Backend suite completa 1796 OK; `makemigrations --check` sin cambios; bandit sin hallazgos; mypy sin errores nuevos en los archivos modificados. Frontend `ng test` 1471 OK, `ng lint` limpio, `i18n:check` 0 faltantes, `ng build` correcto; `npm audit`: 2 moderadas sin relación con el diff. Todos los AC, INV y API-01..04 con verificación real; el diff no contiene la guía ni el script de limpieza; ADR, DDR, PLAN y textos i18n coherentes con el código numérico. Hallazgos nuevos, todos Low: [REV-04](../reviews/REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-04.md) (la prueba de carrera no ejerce `IntegrityError`) y [REV-05](../reviews/REV-2026-11-16-administrar-cuentas-codigo-clasificacion-estado-05.md) (longitud del código sin recortar en el cliente). REV-02 y REV-03 siguen abiertos. No verificado: revisión visual en navegador, carga con datos reales de producción, interacción con CONT-02, CONT-04 y CONT-12.
- **Corrección de REV-02 a REV-05** (PLAN v4): `has_entries` en el API y campos bloqueados en el diálogo; clave i18n sin uso eliminada; prueba directa de la rama `IntegrityError`; longitud del código medida tras recortar. Los cuatro REV quedan cerrados, a la espera de la re-revisión independiente.

## Publicación
PR #80 (base `task/TASK-configurar-seis-clasificaciones-contables`, apilado sobre el #79) listo para aprobación humana; no se mergea. Al mergear el #79 a `accounting`, hay que cambiar la base de este PR a `accounting`. Cambio sensible: contrato de datos de Contabilidad (ADR `modelo-de-cuenta`) con migración aditiva `0008`. REV-01 a REV-05 corregidos y cerrados (PLAN v4); pendiente la re-revisión independiente de esas correcciones.
