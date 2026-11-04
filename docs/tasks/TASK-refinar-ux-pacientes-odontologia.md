# TASK-refinar-ux-pacientes-odontologia: Refinar la experiencia de Pacientes (Odontología)

**Etapa actual:** REVIEW
**Veredicto de complejidad:** NEEDS_PLAN
**Diseño requerido:** SI
**Rama:** task/TASK-refinar-ux-pacientes-odontologia
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/54

## Historial de transiciones
| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-04 | (nuevo) → INVESTIGATION | Task creado a partir de la crítica de diseño de Odontología → Pacientes | delivery-start |
| 2026-11-04 | INVESTIGATION → DESIGN → PLANNING | Veredicto NEEDS_PLAN; DDR escrito; sin ADR | delivery-start |
| 2026-11-04 | PLANNING → ENGINEERING | Specification READY; PR abierto | delivery-start |
| 2026-11-04 | ENGINEERING → REVIEW | Implementación y pruebas de la Specification; se solicita Quality Gate independiente | delivery-build |

## Investigación

### Requerimiento
Insumo, no Specification aprobada: la crítica de diseño (`/design:design-critique`) del flujo Odontología → Pacientes en PocketBiz, hecha en esta misma sesión con 5 capturas (lista, alta de cliente en el modal, selección de cliente, ficha, ficha en edición clínica). Se pidió mejorar el UX/UI manteniendo el texto en español, el sistema de diseño y las reglas de acceso (módulos Clientes y Odontología, permiso clínico, aislamiento por empresa). Quedan fuera citas, facturación, odontograma y planes de tratamiento.

Decisión de alcance tomada aquí (sin decisión de negocio abierta): se implementa solo lo que **la funcionalidad actual ya soporta** (frontend). Lo que exige backend o regla de negocio queda como propuesta en «Out of scope» del PLAN, sin tocarlo.

### Hechos encontrados
- `frontend/panel_admin/src/app/features/dentistry/pages/patient-create.component.html:12-39` — el modal usa «Cliente», «Crear cliente nuevo» y `Crear ficha clínica`; la creación rápida se abre sustituyendo el contenido del modal (`:9-10`, `opening`).
- `patient-create.component.ts:53-62` — al seleccionar se hace `api.get` para saber si ya hay ficha; mientras `checking` el botón queda deshabilitado sin motivo visible (`.html:42`).
- `patient-create.component.ts:75-83` y `.html:10` — tras crear el cliente solo se selecciona (`select($event)`); la persona debe pulsar de nuevo para crear la ficha.
- `patient-create.component.html:20` — literal `' · Inactivo'` hardcodeado (incumple la regla de i18n de `CLAUDE.md`).
- `frontend/panel_admin/src/app/features/customers/components/customer-quick-create/customer-quick-create.component.ts:28-29,47-58,74-97` — componente compartido (también lo usan pedidos); modo `embedded`, emite `created`; duplicado de teléfono por `Swal` (`:61-72`).
- `patient-detail.component.html:3-8` — un solo `error` y un solo `success` globales arriba de la página; `.ts:93-121` — `saveClinical` y `saveAdmin` los sobrescriben (mensajes de un guardado pisan al otro).
- `patient-detail.component.html:21,46,89` — «Editar ficha» (abre ambas secciones) coexiste con un botón de edición por tarjeta.
- `patient-detail.component.html:23` y `.ts:122-133` — «Archivar perfil» (outline-warning, con un hack de contraste en `.ts:22-24`) junto a Editar; confirma con `window.confirm`; el perfil archivado oculta (no deshabilita) los botones de edición (`.html:20,46,89`).
- `patient-detail.component.html:34-35` — primera fila de «Información general» es el UUID del cliente.
- `patient-detail.component.html:28-118` — orden: columna izquierda (identidad, nacimiento/responsable), derecha (antecedentes); alergias y medicación son las filas 3 y 4 del bloque clínico (`.ts:2-8`).
- `patient-detail.component.html:55-63,74-78` — badge «Menor de edad» sin edad; campos del responsable con `aria-required` pero sin marcador visual; el responsable solo se muestra si el valor del formulario es menor de edad.
- `patient-detail.component.html:98` — el placeholder del textarea reutiliza «No informado» (parece un valor); `rows="2"`, `maxlength="4000"` sin contador.
- `patient-detail.component.html:54,59,62,99` — mensajes de error en `<small>` sin `aria-invalid` ni `role="alert"`; `.ts:80-92,93-106` — sin gestión del foco al abrir, guardar o cancelar.
- `patient-detail.component.html:120-131` y `components/patient-history.component.ts:13,76-94` — dos historiales (administrativo y clínico) lado a lado en un `<details>`, con paginación independiente; antes/después como texto plano; `labels[key] ?? key` muestra la clave cruda si falta etiqueta.
- `pages/patient-list.component.html:25-34` — columnas Paciente/Teléfono/Estado/Acciones; `:18-21` — «Limpiar filtros» solo en el estado vacío; `:10-11` sin ayuda sobre el formato de teléfono.
- `backend/modules/dentistry/application/patients.py:58-68` — el resumen del listado ya incluye `birth_date`, `responsible_*`, `updated_at` y `active`; no incluye texto clínico.
- `backend/modules/dentistry/api/views.py:81-88` — crear perfil requiere solo `customer_id`; `PatientListView.get` acepta `search`, `active`, `page`, `page_size`.
- `frontend/panel_admin/src/app/core/guard/unsaved-changes.guard.ts:11-12` — la guardia de salida usa `window.confirm` (compartida con otras pantallas).
- `frontend/panel_admin/src/app/features/dentistry/services/demographics-form.ts:6-19` — `minorAt` y `demographicsValidator`: el responsable es obligatorio si es menor de 18 **o** si se informó alguno de los dos datos.
- `docs/design/DDR-perfil-odontologico-pacientes-ficha-y-listado.md:20` — decisión vigente: vacío clínico muestra «No informado» y nunca «Sin alergias»; `:26-30` — revisión de interfaz de 2026-11-03.
- `docs/design/design-system.md:106-125` — plantillas Lista y Detalle (estas pantallas ya las siguen); `:84-93` — botones; `:95-104` — estados obligatorios.

### Hipótesis / supuestos no confirmados
- No se vieron en ejecución: estado archivado, menor de edad, historial expandido, errores, móvil, tema oscuro ni la UI en español (las capturas están en inglés). Los hallazgos sobre esos estados salen del código y deben verificarse en `delivery-publish`.
- Contraste del botón de ojo gris, de los botones primarios deshabilitados y del campo de búsqueda teñido: no medido.
- Se asume que reemplazar `window.confirm` por el diálogo `Swal` ya usado en Clientes es coherente con el sistema de diseño (no hay un componente de diálogo compartido en `shared/`).
- Cambiar la etiqueta «No informado» por «Sin registrar» en la ficha es un cambio de copy, no de comportamiento: la invariante «vacío ≠ ausencia declarada» se conserva. La persona puede vetarlo en el PR.

### Módulos y dependencias relacionadas
`frontend/panel_admin/src/app/features/dentistry/` (páginas, componente de historial, servicios); `features/customers/components/customer-quick-create` (compartido con pedidos: cualquier cambio debe ser retrocompatible); `assets/i18n/{es,en,pt}.json`; `docs/design/`. Backend sin cambios.

### Implementaciones similares existentes
Detalle con historial embebido (`features/inventory/pages/stock-detail`) y diálogo de acción con motivo (`features/inventory/components/movement-reverse-dialog`, `features/purchases/components/receipt-revert-dialog`) del sistema de diseño §5.

### Comportamiento actual
Funcional y cubierto por pruebas; los problemas son de claridad, jerarquía y feedback (ver crítica).

### Restricciones
`CLAUDE.md`: sin texto hardcodeado (claves en es/en/pt con las mismas claves, `npm run i18n:check`), Reactive Forms, sin `any`, sin suscripciones colgadas, `provideTestTranslations()` en pruebas, sin dependencias nuevas, backend no es barrera de seguridad (se conserva `clinicalGuard` y el permiso del backend).

### Riesgos identificados
- Cambiar `CustomerQuickCreateComponent` afecta a pedidos: solo con inputs opcionales y valores por defecto iguales a los actuales.
- Encadenar crear cliente + crear perfil no es atómico: si falla el segundo paso queda un cliente sin ficha (se mitiga en UI; atomicidad real requiere backend).
- Muchas claves i18n nuevas en tres idiomas: riesgo de claves faltantes (lo detectan las pruebas existentes).
- Las pruebas de componentes actuales dependen de textos y estructura de la ficha; habrá que actualizarlas.

### Veredicto de complejidad
**NEEDS_PLAN** — cambio acotado a un módulo de frontend, sin contrato API, migraciones, permisos ni decisión arquitectónica nueva.

### Diseño requerido
**SI** — cambia el flujo del modal de alta, la jerarquía de la ficha y el patrón de edición/guardado.

## Diseño
Ver `docs/design/DDR-refinar-ux-pacientes-odontologia-registro-ficha-y-listado.md`.

## Arquitectura
No aplica según veredicto.

## Plan
`docs/plans/PLAN-2026-11-04-refinar-ux-pacientes-odontologia.md` (v1, COMPLETO, Specification READY).

## Implementación
Solo frontend (`frontend/panel_admin/`); sin cambios en backend, endpoints, permisos ni migraciones. Sin dependencias nuevas.

| AC / INV | Parte implementada |
|---|---|
| AC-01…07 | `patient-create.component.{ts,html}`: modal en una pantalla (texto introductorio, «Buscar cliente», «¿No está? Registrar persona nueva», «Crear paciente»/«Registrar paciente»/«Abrir ficha»), `customerCreated()` encadena la creación del perfil, `profileFailed` + «Reintentar» conserva el cliente, aviso informativo «ya es paciente», motivo del botón deshabilitado, «Inactivo» por clave i18n |
| AC-02 | `CustomerQuickCreateComponent`: `@Input() submitLabel` y `backLabel` opcionales (por defecto, textos anteriores; spec de compatibilidad) |
| AC-08…11 | `patient-list.component.{ts,html}`: columnas Edad (badge «Menor») y Actualizado, ayuda del buscador, «Limpiar filtros» condicional, vacíos diferenciados; `ageAt()` en `demographics-form.ts` |
| AC-12…15, 22, 23 | `patient-detail.component.{ts,html}`: ficha reordenada (Resumen clínico → Antecedentes → Datos personales → Contacto → Registro), sin UUID ni «Editar ficha», «Sin registrar» + «Registrar», edad y aviso de menor, banner de archivado, botones «Editar» deshabilitados con `title`, confirmación `Swal` (`confirmStateChange`) |
| AC-16…21 | Estado por sección (`clinicalState`/`adminState`, `statusText()`), sin banners globales de guardado, `aria-invalid`/`role="alert"`, foco, contador desde 3 200, textareas autoajustables, placeholders de ejemplo (`CLINICAL_FIELDS[].placeholder`) |
| AC-24, 25 | `patient-history.component.ts` (recorte con «Mostrar texto completo», etiqueta neutra, acciones legibles) y pestañas en la ficha |
| AC-26 | Claves nuevas/ajustadas/eliminadas en `es/en/pt.json` (mismas claves) |
| INV-01…04 | Sin cambios de regla; cubiertas por pruebas de la ficha |

**Pantallas de referencia seguidas:** Lista (`product-list`) y Detalle (`product-detail`), según DDR. **Componentes compartidos:** `ngx-datatable`, `ng-select`, `app-customer-quick-create` (extendido con inputs opcionales), badges `badge-outline`, `Swal` ya usado en Clientes. Sin componente nuevo en `shared/`. `docs/design/design-system.md` actualizado con el patrón «Detalle con edición por sección y línea de estado».

**Verificación propia (no es el Quality Gate):** `npm test` → 1199 correctas, 1 fallo (`screens-i18n.spec.ts` «labels coming from code follow the active language»), que **también falla en `origin/main` limpio** (reproducido en un checkout aparte, 2 de 2 veces; el mensaje cambia entre «Entregado»/«Entregue»); no se tocó. `npm run lint` y `npm run i18n:check` limpios; `ng build` correcto (solo avisos Sass previos). Para ejecutar las pruebas en el worktree se enlazó `node_modules` del checkout principal mediante una junction (ignorada por git).

**Desviaciones respecto al plan:**
- En modo edición de la ficha, los campos del responsable siguen apareciendo solo para menores (como antes); el plan no pedía mostrarlos siempre.
- La línea de estado «Guardado ✓» permanece hasta la siguiente edición (no se desvanece); el AC no exigía desvanecerla.
- «Sin cambios» se muestra en la línea de estado de la sección (no dentro del botón); el botón queda deshabilitado.
- La creación rápida sigue reemplazando el contenido del modal (vista «Registrar persona nueva» con «Volver a buscar»), dentro del mismo modal.

**Deuda técnica / pendiente de verificación visual (para publish):** estados archivado, menor, historial expandido, móvil, tema oscuro y UI en español no se vieron en ejecución; contraste de botones deshabilitados; `unsavedChangesGuard` sigue usando `window.confirm` (compartido); `Swal` sin componente compartido; «Sin registrar» vs «No informado» en otras fichas.

## Review
_Pendiente_

## Publicación
_Pendiente_
