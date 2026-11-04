# PLAN-2026-11-04-refinar-ux-pacientes-odontologia (v1)

**Task:** TASK-refinar-ux-pacientes-odontologia · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** `docs/design/DDR-refinar-ux-pacientes-odontologia-registro-ficha-y-listado.md` / Ninguno

Modo COMPLETO por el eje 3 (DDR con impacto visual relevante: cambia el flujo del alta, la jerarquía de la ficha y el patrón de guardado). No hay dominio, contrato API ni migraciones.

## Objective
Hacer más directo el alta de pacientes, que la ficha ponga lo clínico por delante y que editar/guardar sea predecible sección por sección, usando solo la funcionalidad que el backend ya expone.

## Context
Ver `docs/tasks/TASK-refinar-ux-pacientes-odontologia.md` (hechos con `archivo:línea`). Refina, sin reemplazar, la Specification de `PLAN-2026-11-02-perfil-odontologico-pacientes`.

# Specification

## Domain context
Contexto Odontología (frontend `features/dentistry`), que lee Clientes mediante la API existente. Sin cambios de dominio ni de backend.

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Paciente | Cliente con perfil odontológico (mismo id) | TASK-perfil-odontologico-pacientes |
| Ficha | Pantalla de detalle del paciente | DDR vigente |
| Antecedentes | Los cinco campos clínicos de texto libre | `models/patient.ts:2-8` |
| Datos personales | Fecha de nacimiento y responsable (viven en el cliente) | `customers` demographics |
| Registro de cambios | Auditoría de ediciones/estado (no es historia clínica ni línea de tratamiento) | `patient-history.component.ts` |
| Sin registrar | Campo clínico vacío: no se preguntó o no se informó; **nunca** equivale a «sin alergias» | DDR vigente (copy nuevo) |

## Current behavior
Ver TASK, «Hechos encontrados». Resumen: el alta usa lenguaje de datos y obliga a un clic extra tras crear el cliente; la ficha tiene un mensaje global de guardado, edición global y por tarjeta a la vez, UUID visible y lo clínico en una columna secundaria; el historial muestra dos listas paralelas.

## Expected behavior
Ver ACs. Sin cambios en endpoints, permisos, reglas de menores ni archivo sin borrar.

## Domain rules / invariants
- **INV-01 (existente):** un campo clínico vacío nunca se muestra como ausencia declarada («Sin alergias», «Ninguna»…).
- **INV-02 (existente):** menor de 18 con nacimiento conocido exige nombre y teléfono del responsable; si se informó uno, se exige el otro (`demographics-form.ts:15`).
- **INV-03 (existente):** un perfil archivado no se edita (UI y backend 409).
- **INV-04 (existente):** un cliente tiene un solo perfil; crear uno ya existente devuelve 409.

## Acceptance criteria
**Alta (modal «Nuevo paciente»)**
- **AC-01** El modal se muestra en una sola pantalla con título «Nuevo paciente», texto introductorio y el selector «Buscar cliente»; no aparece la palabra «ficha clínica» en el botón ni «cliente» como título de paso.
- **AC-02** «¿No está? Registrar persona nueva» abre dentro del mismo modal el formulario rápido (Nombre obligatorio, Teléfono opcional) con «Volver a buscar». Se reutiliza `CustomerQuickCreateComponent` con inputs opcionales para etiquetas; sin esos inputs se comporta exactamente como hoy (pedidos).
- **AC-03** Al enviar el formulario rápido se crea el cliente y, a continuación y sin otro clic, el perfil; al terminar se abre la ficha con el aviso «Perfil creado» y el foco en la primera sección clínica.
- **AC-04** Si el cliente se creó pero falla la creación del perfil, el modal permanece abierto con el cliente seleccionado, muestra «Se registró a {nombre} como cliente, pero no se pudo crear su ficha.» y un botón «Reintentar» que crea solo el perfil (no duplica el cliente).
- **AC-05** Al seleccionar un cliente con perfil existente se muestra un aviso informativo «{nombre} ya es paciente.» y el botón principal pasa a «Abrir ficha» (sin mensaje de error). Un 409 al crear produce el mismo estado.
- **AC-06** El botón principal deshabilitado muestra su motivo en texto («Elige o registra a una persona» / «Comprobando si ya es paciente…»). El texto del botón es «Crear paciente» (cliente existente), «Registrar paciente» (persona nueva) o «Abrir ficha».
- **AC-07** El duplicado de teléfono conserva el diálogo existente («Crear de todos modos»). La etiqueta «Inactivo» de una opción sale de una clave i18n (sin literal en la plantilla).

**Lista**
- **AC-08** La tabla añade las columnas Edad (años; badge «Menor» si < 18; «—» sin nacimiento) y Actualizado (`dd/MM/yyyy`). Se conservan Paciente, Teléfono, Estado y Acciones.
- **AC-09** El buscador muestra ayuda: «Busca por nombre o teléfono. Se ignoran espacios y guiones.»
- **AC-10** «Limpiar filtros» es visible siempre que haya búsqueda o el estado sea distinto de Activos, y restablece búsqueda, estado y página 1. Los filtros siguen en la URL y se conservan al volver de la ficha.
- **AC-11** Vacío sin ningún paciente: «Aún no hay pacientes. Registra el primero con «Nuevo paciente».» Vacío con filtros: «No hay pacientes que coincidan…» con sugerencia de probar «Todos» cuando el estado no es Todos.

**Ficha: estructura**
- **AC-12** La cabecera muestra nombre, badges (Activo/Archivado, y «Menor · N años» si aplica) y línea de contacto con enlace «Ver cliente»; el UUID no se muestra. Desaparece el botón global «Editar ficha».
- **AC-13** El orden es: Resumen clínico (Alergias, Medicación) → Antecedentes (médicos, odontológicos, observaciones) → Datos personales → Contacto (solo lectura, con la nota de que se edita en Clientes) → Registro de cambios. En móvil lo clínico va primero.
- **AC-14** Un campo clínico vacío se muestra «Sin registrar» en estilo neutro, con enlace «Registrar» que abre la edición de su sección (INV-01). Nunca «Sin alergias».
- **AC-15** «Archivar perfil»/«Reactivar perfil» usa `btn-warning`, sin el hack de contraste, y pide confirmación en un diálogo `Swal` (no `window.confirm`) cuyo texto explica el efecto: archivar conserva todos los datos y bloquea la edición; reactivar permite volver a editar. Bloqueado con cambios sin guardar, mensaje con el nombre de la sección pendiente.

**Ficha: edición y guardado**
- **AC-16** Cada sección (Antecedentes, Datos personales) se edita y guarda por separado; la sección abierta muestra la etiqueta «Editando» y botones «Guardar antecedentes» / «Guardar datos personales» y «Cancelar». Ningún texto usa «historial» para los antecedentes.
- **AC-17** Cada sección tiene su propia línea de estado con `aria-live="polite"`: «Cambios sin guardar» · «Guardando…» · «Guardado ✓» · «No se pudo guardar. Tus cambios siguen aquí.» con «Reintentar». Si una sección guarda y la otra falla, cada línea refleja su propio resultado. Se eliminan los banners globales de resultado de guardado; se conservan el de carga de la ficha y el de «Perfil creado».
- **AC-18** Con la sección sin cambios, el botón de guardar muestra el motivo («Sin cambios»). Las validaciones del servidor (400) se muestran bajo el campo con `aria-invalid="true"`, `role="alert"` y se enfoca el primer campo inválido.
- **AC-19** Los textareas crecen con el contenido; desde 3 200 caracteres se muestra el contador «n / 4000». El placeholder es un ejemplo (p. ej. «Ej.: penicilina, látex»), nunca «No informado»/«Sin registrar».
- **AC-20** Foco: al abrir una sección va al primer campo; al guardar o cancelar vuelve al botón «Editar» de esa sección.
- **AC-21** Se conserva la guardia de salida con cambios sin guardar (`unsavedChangesGuard`, `beforeunload`).

**Ficha: menores y archivada**
- **AC-22** Con nacimiento informado se muestra la edad junto a la fecha («12/03/2014 · 12 años»). Si es menor se muestra «Menor de 18 años: indica quién es responsable.», y los campos del responsable llevan marcador visible «Obligatorio» (INV-02). En lectura, un menor sin responsable muestra «Falta el responsable (obligatorio para menores).»
- **AC-23** Un perfil archivado muestra un banner «Perfil archivado — solo lectura. Reactiva el perfil para editarlo.» con la acción «Reactivar perfil»; los botones «Editar» aparecen deshabilitados con `title` explicativo; el contenido sigue legible (INV-03).

**Registro de cambios**
- **AC-24** El bloque se llama «Registro de cambios», sigue plegado por defecto y contiene pestañas «Antecedentes» y «Datos personales» (una lista visible a la vez), cada una con su paginación.
- **AC-25** Cada entrada muestra acción («Perfil creado», «Datos editados», «Perfil archivado», «Perfil reactivado»), autor y fecha `dd/MM/yyyy HH:mm`; antes/después apilados; los textos de más de 200 caracteres se recortan con «Mostrar texto completo»; un campo sin etiqueta conocida muestra una etiqueta neutra, no su clave.

**Transversales**
- **AC-26** Toda cadena visible nueva está en `es.json`, `en.json` y `pt.json` con las mismas claves (español es la referencia); `npm run i18n:check`, `npm run lint`, `npm test` y `npm run build` pasan.
- **AC-27** No hay cambios en el backend ni en endpoints, permisos o `company_id`; `clinicalGuard` y «Acceso no disponible» se conservan.

## Edge cases / Error cases
- **EDGE-01** Búsqueda de cliente falla: se conserva el mensaje con «Reintentar búsqueda».
- **EDGE-02** Teléfono duplicado al registrar persona nueva: diálogo existente; si cancela, no se crea nada.
- **EDGE-03** Doble clic en «Registrar paciente»: una sola cadena de peticiones (`saving`).
- **EDGE-04** Cambiar la fecha a adulto con datos de responsable ya guardados: se conserva el comportamiento actual (validador, `demographics-form.ts:15`); no se oculta el error si queda uno solo de los dos.
- **EDGE-05** Fallo al cargar el historial de una pestaña: error con «Reintentar» solo en esa pestaña.
- **EDGE-06** Perfil archivado desde otra sesión mientras se edita: el guardado devuelve 409; se muestra el error en la línea de estado de la sección y se conserva el texto escrito.

## Authorization / permissions
Sin cambios. Backend: `CompanyClinicalPermission`, módulos `dentistry` y `customers`, aislamiento por `company_id`. La UI no concede ni simula acceso.

## API contract
Sin cambios. Se usan los endpoints existentes (`GET/POST /api/dentistry/patients/`, `GET/PATCH …/:id/`, `POST …/archive|activate/`, `GET …/history/`, `PATCH /api/customers/:id/demographics/` y su historial, `POST /api/customers/`).

## UI behavior
- **UI-01** Lista: plantilla Lista (§5) del sistema de diseño; AC-08…AC-11.
- **UI-02** Modal: modal grande existente (`NgbModal`, `backdrop: 'static'`), `ng-select`; AC-01…AC-07.
- **UI-03** Ficha: plantilla Detalle (§5) con `.card`, `dl`, badges `badge-outline`/Bootstrap subtle, botones §3; AC-12…AC-23.
- **UI-04** Registro de cambios: `<details>` + `nav-tabs`; AC-24, AC-25.
- **UI-05** Estados §4: cargando (texto/skeleton), vacío, error de validación, error de servidor, éxito y sin permiso cubiertos en cada pantalla.
- **UI-06** Responsive: lista legible hasta 360 px (scroll horizontal del datatable ya existente); ficha apilada con lo clínico primero; claro y oscuro con clases de la plantilla.

## Non-functional requirements
Accesibilidad mínima (§7 del sistema): labels asociados, foco visible, errores asociados con `aria-describedby`, regiones `aria-live` para estados, botones solo-icono con `title` y `aria-label`. Sin HEX ni fuentes sueltas.

## Out of scope
Requieren backend o decisión de negocio y **no** se tocan:
- etiqueta «Ya es paciente» en los resultados del selector de clientes;
- confirmación explícita «Sin alergias conocidas» (quién y cuándo) y su visibilidad;
- indicador de alergias/medicación en el listado;
- historial unificado y filtrable en un solo endpoint;
- `archived_at`/`archived_by` en el perfil (el banner no muestra fecha ni autor);
- control de concurrencia optimista (hoy gana la última escritura);
- endpoint atómico «crear cliente + paciente»;
- política sobre clientes inactivos (se mantiene que pueden seleccionarse);
- política sobre datos de responsable de adultos; búsqueda por correo/fecha;
- citas, facturación, odontograma, planes de tratamiento.

## Open questions
- (No bloquea) ¿Se conserva «Sin registrar» o se vuelve a «No informado» tras verlo en la UI? Revisión en `delivery-publish`.

# Test Specification

## Unit tests / Integration tests
Karma/Jasmine con `provideTestTranslations()`; sin nuevos mocks de backend más allá de los servicios existentes.
- `patient-create.component.spec.ts`: AC-01…AC-07, EDGE-01…03 (cadena cliente→perfil, fallo del segundo paso y reintento sin duplicar cliente, aviso «ya es paciente», 409, motivos del botón).
- `customer-quick-create.component.spec.ts`: inputs opcionales de etiquetas; comportamiento por defecto intacto (pedidos).
- `patient-list.component.spec.ts`: AC-08…AC-11.
- `patient-detail.component.spec.ts`: AC-12…AC-23, EDGE-04, EDGE-06 (orden de secciones, «Sin registrar» sin «Sin alergias», edición/estado por sección, guardado parcial, contador, foco, confirmación `Swal`, banner de archivado).
- `patient-history.component.spec.ts`: AC-24, AC-25, EDGE-05.
- `demographics-form.spec.ts`: sin cambios; se añade caso para el cálculo de edad si se crea un helper.
- Prueba de i18n existente + `npm run i18n:check`: AC-26.

## E2E
**NO** — no hay flujo crítico nuevo de punta a punta ni cambios de integración; los flujos se cubren con pruebas de componente. No requiere dependencias.

## Regression tests
Suite completa del frontend (`npm test`), `npm run lint`, `npm run build`. Verificación manual/visual de los estados no vistos: archivado, menor, historial expandido, errores, móvil, tema oscuro y UI en español (en `delivery-publish`).

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, 02 | `patient-create.component.spec.ts`, `customer-quick-create.component.spec.ts` |
| AC-03, 04 | `patient-create.component.spec.ts` (cadena y reintento) |
| AC-05, 06 | `patient-create.component.spec.ts` |
| AC-07 | `patient-create.component.spec.ts` + `i18n:check` |
| AC-08…11 | `patient-list.component.spec.ts` |
| AC-12…15 | `patient-detail.component.spec.ts` |
| AC-16…21 | `patient-detail.component.spec.ts` (+ `unsaved-changes` existente) |
| AC-22, 23 | `patient-detail.component.spec.ts`; revisión visual en publish |
| AC-24, 25 | `patient-history.component.spec.ts`, `patient-detail.component.spec.ts` |
| AC-26 | prueba de i18n, `npm run i18n:check`, `npm run lint`, `npm run build` |
| AC-27 | revisión de diff (sin cambios en `backend/`) |

# Implementation Plan

## Architecture considerations
Solo frontend. La lógica no visual (edad, estado de guardado por sección, recorte de texto, etiquetas de acción) va en helpers/servicios inyectables de `features/dentistry/services/`, no en plantillas. `CustomerQuickCreateComponent` recibe `@Input()` opcionales (`submitLabel`, `backLabel`, `title`, `showTitle`) con valores por defecto iguales a los actuales.

## Proposed solution
1. Modal: reorganizar `patient-create` en una vista con selector + panel de registro rápido embebido; encadenar `customers.create` (vía el componente rápido) con `api.create`; manejar el fallo del segundo paso conservando el cliente.
2. Lista: añadir columnas Edad y Actualizado, ayuda del buscador, «Limpiar filtros» condicional y mensajes de vacío.
3. Ficha: reordenar plantilla, retirar UUID y edición global, estado de guardado por sección (`idle | dirty | saving | saved | error`), foco, contador y autoajuste de textareas, banner de archivado, confirmaciones `Swal`.
4. Historial: pestañas, entradas legibles, recorte con «Mostrar texto completo», etiquetas neutras.
5. i18n en es/en/pt y actualización del sistema de diseño (patrón «Edición por sección con línea de estado»).

## Files/components affected
- Frontend: `features/dentistry/pages/{patient-create,patient-list,patient-detail}.component.{ts,html,spec.ts}`, `features/dentistry/components/patient-history.component.{ts,spec.ts}`, `features/dentistry/services/` (helper de edad/estado), `features/dentistry/models/patient.ts` (si hace falta), `features/dentistry/testing/patient-fixtures.ts`, `features/customers/components/customer-quick-create/*` (inputs opcionales + spec), `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` (patrón nuevo, tras implementar), este PLAN y el TASK.
- Backend, migraciones: ninguno.

## Implementation steps
1. Inputs opcionales en `CustomerQuickCreateComponent` + prueba de compatibilidad (AC-02).
2. Alta en una pantalla con cadena y reintento (AC-01, 03…07).
3. Lista (AC-08…11).
4. Ficha: estructura y vacíos (AC-12…15, 22, 23).
5. Ficha: edición, estados por sección y accesibilidad (AC-16…21).
6. Historial (AC-24, 25).
7. i18n es/en/pt y revisión de la paridad de claves (AC-26).
8. Actualizar pruebas existentes, `design-system.md`; ejecutar `i18n:check`, lint, test y build (AC-26, 27).

## Database / migrations
Ninguna.

## Risks
- Regresión en pedidos por el componente de alta rápida compartido → inputs opcionales y spec de compatibilidad.
- Pruebas de ficha existentes frágiles por cambios de texto/estructura → reescribir por rol/`data-testid`.
- Cadena no atómica cliente→perfil → mitigación de UI (AC-04); atomicidad real requeriría backend (fuera de alcance).
- Contraste y estados no vistos → verificación visual en publish.

## New dependencies
Ninguna.
