# TASK-configurar-horarios-y-disponibilidad: PB-AGE-001

**Etapa actual:** PUBLISH
**Veredicto de complejidad:** NEEDS_ARCHITECTURE
**Diseño requerido:** SI
**Rama:** task/TASK-configurar-horarios-y-disponibilidad
**Pull Request:** https://github.com/rolion/dore-mini-erp/pull/49
**Fuente:** https://trello.com/c/7MIst1PV/

## Historial de transiciones

| Fecha (UTC) | Transición | Motivo | Origen |
|---|---|---|---|
| 2026-11-03 | (nuevo) → INVESTIGATION | Tarjeta y documentos contrastados con el código | delivery-start |
| 2026-11-03 | INVESTIGATION → DESIGN | Nueva vista semanal y formularios | delivery-start |
| 2026-11-03 | DESIGN → ARCHITECTURE | Agenda consume Personal y persiste reglas propias | delivery-start |
| 2026-11-03 | ARCHITECTURE → PLANNING | Pendiente definir la fuente de zona horaria y turnos nocturnos | delivery-start |

| 2026-11-03 | PLANNING → ENGINEERING | Alcance temporal confirmado y PR #49 abierto | delivery-start |
| 2026-11-03 | ENGINEERING → REVIEW | Implementación publicada y verificaciones pendientes registradas | delivery-build |
| 2026-11-03 | REVIEW → ENGINEERING | FAIL del Quality Gate independiente | delivery-publish |

| 2026-11-03 | ENGINEERING → REVIEW | Hallazgos corregidos y 122 pruebas aprobadas en PostgreSQL | delivery-build |

| 2026-11-03 | REVIEW → ENGINEERING | Tercer FAIL; la persona autorizó corregir REV-06 a REV-12 | delivery-publish |
| 2026-11-03 | ENGINEERING → REVIEW | Hallazgos corregidos; pendiente un gate con acceso a PostgreSQL | delivery-build |

| 2026-11-03 | REVIEW → PUBLISH | Cuarto Quality Gate: PASS con REV-13 (Medium) y REV-14 (Low) como limitaciones conocidas | delivery-publish |

## Investigación

### Requerimiento

[PB-AGE-001](https://trello.com/c/7MIst1PV/) pide configurar turnos semanales con vigencia y pausas, y ausencias por profesional con motivo administrativo. Los turnos contiguos se permiten; los solapados se rechazan. La vista semanal indica la zona horaria y distingue los estados con texto. La ausencia 10:00–11:00 bloquea ese intervalo de un turno 09:00–12:00. Las reservas y el bloqueo por citas futuras afectadas se integran en PB-AGE-002. Un consultorio por empresa, sin sucursales ni recursos físicos. La tarjeta no tiene etiquetas, checklists ni comentarios. La tarjeta y los documentos de [historias](https://docs.google.com/document/d/1pn3nChDn9MRH4wlLCTYWYfHop1sWJfcWVfR0gG6fTHQ) y [especificaciones](https://docs.google.com/document/d/1hH2IGXc-KKod9RAMzfjtnvdg7YvA5CBQKDZABBGS1f8) son insumos.

### Hechos encontrados

- `backend/config/urls.py:6` y `backend/modules/modularity/domain/modules.py:18`: Personal ya está integrado; el catálogo todavía no registra Agenda.
- `backend/modules/personnel/infrastructure/django/models.py:27`: Personal ya posee la entidad persistida de profesional.
- `backend/modules/accounts/models.py:8` y `backend/config/settings/base.py:73`: Company no tiene zona horaria; Django usa un ajuste global que por defecto es UTC.
- `backend/shared/tenancy.py:12` y `backend/config/permissions.py:27`: el backend deriva la empresa de sesión y controla acceso por módulo.
- `docs/design/design-system.md:94`, `:114` y `:135`: patrones para estados, formularios y pantalla de configuración.

### Decisiones confirmadas

- El usuario confirmó que Agenda usa la zona de Bolivia en esta versión y que la configuración por empresa queda para el futuro.
- El usuario confirmó que esta versión no admite turnos nocturnos. Cada turno empieza y termina el mismo día.

### Veredictos

**NEEDS_ARCHITECTURE:** nuevo contexto con persistencia, relación con Personal, control de concurrencia y un contrato temporal que consumirá Citas.
**Diseño requerido: SI:** vista semanal nueva con dos formularios y estados de accesibilidad.

## Diseño

[DDR de la vista semanal](../design/DDR-configurar-horarios-y-disponibilidad-vista-semanal.md).

## Arquitectura

[ADR de límites y tiempo](../adr/ADR-configurar-horarios-y-disponibilidad-limites-y-tiempo.md).

## Plan

**Specification readiness: READY.** [Plan v1](../plans/PLAN-2026-11-03-configurar-horarios-y-disponibilidad.md), modo COMPLETO. Documentación publicada en el PR #49.

## Implementación

El commit `5f6fba6` implementa la API de Agenda, la migración aditiva y la vista semanal en el PR #49.

- AC-01. La API exige rol administrativo y los módulos Agenda y Personal. Las consultas se acotan a la empresa de sesión.
- AC-02 y AC-03. El dominio valida vigencia, pausas y solapamientos y calcula disponibilidad al descontar pausas y ausencias. El guardado de turnos se serializa por empresa y profesional.
- AC-04. La vista agrupa intervalos por día en hora de Bolivia y reutiliza la tarjeta, el breadcrumb y los controles de formulario del panel. Los formularios usan diálogos nativos y enfocan el mensaje de error cuando falla el guardado.

Comprobaciones de ingeniería: tres pruebas de dominio, compilación Angular y `manage.py check`. `makemigrations --check --dry-run` no detectó diferencias entre modelos y migraciones, pero no pudo consultar el historial en PostgreSQL. La suite posterior aplicó las migraciones en PostgreSQL 16 y aprobó 122 pruebas, incluidas las de permisos, aislamiento, alta, edición, zona horaria y concurrencia. La compilación de plantillas Angular pasó con ngc. Pendiente el recorrido visual y de teclado en navegador.

Corrección del tercer gate (REV-06 a REV-12):

- REV-06. `sidebar-menu.spec.ts` incluye el menú Agenda (12 rutas, 33 títulos). Karma completo: 1121 pruebas correctas; cobertura 86,21 % sentencias, 77,95 % ramas.
- REV-07. Los diálogos usan fondo, texto y borde del tema oscuro (`:host-context(.dark)`).
- REV-08. `dialogError` separado de `error`: el error de guardado vive solo en su diálogo y se limpia al abrirlo.
- REV-09. Frontend: `models/agenda.ts` y `services/agenda-api.service.ts` (con spec). Backend: el cálculo de disponibilidad pasó a `application/week.py`. Desviación: la vista conserva el control de solapamiento y de bloqueo dentro de la transacción, como fija el ADR; no se creó capa de comandos adicional.
- REV-10. Nuevas pruebas de dominio (pausas inválidas, vigencias adyacentes y coincidentes, ausencias central, de varios días y superpuestas) y de API (usuario sin empresa activa, turno ajeno, pausas y turno nocturno inválidos, turnos contiguos, ausencias de varios días y superpuestas).
- REV-11. Fechas `dd/MM/yyyy HH:mm` y texto «Sin turnos ni ausencias» en los días vacíos.
- REV-12. Este bloque actualiza el TASK.

Verificación propia de ingeniería (no es el Quality Gate): lint y build de Angular correctos; 14 pruebas backend sin base de datos correctas. **Las pruebas de API no se ejecutaron** (sin credenciales de PostgreSQL); solo compilan. Recorrido visual en navegador pendiente.

## Review

**FAIL** sobre `476397f`. Falló una prueba de límites entre módulos y quedaron sin ejecutar las verificaciones con PostgreSQL. La revisión visual en navegador queda pendiente. El PR #49 sigue en borrador.

- [Falla el límite de arquitectura de Agenda](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-01.md) (High).
- [Faltan pruebas de integración de Agenda](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-02.md) (High).
- [El formulario permite cambios durante el guardado](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-03.md) (Medium).
- [La semana vacía puede quedar sin mensaje](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-04.md) (Medium).

Ingeniería corrigió los cuatro hallazgos, incorporó diálogos nativos y comprobó la integración en PostgreSQL.

**Segundo gate: sin PASS** sobre `ad64a92`. PostgreSQL 16 aprobó 122 pruebas y Django no reportó problemas. El lint de Angular pasó y `npm audit` reportó cero vulnerabilidades. El build y Karma no completaron la compilación. Node 22.12.0 terminó con código Windows 3221225477 y Node 24.22.1 salió con código 1 después de `Building...`. Quedan sin verificar la cobertura, la vista en navegador y la navegación por teclado. El TASK permanece en REVIEW y el PR sigue en borrador.

**Tercer gate: FAIL** sobre `7d521eb`. Build y lint pasan (con `NG_BUILD_MAX_WORKERS=1` y `--max-old-space-size=1536`), `npm audit` sin vulnerabilidades; Karma: 2 fallos de 1118 ([REV-06](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-06.md), High). Otros hallazgos: [07](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-07.md) a [12](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-12.md). La suite backend no se reprodujo en el gate (sin acceso a credenciales de PostgreSQL). Visual verificada solo con backend simulado. Es el tercer resultado sin PASS consecutivo: se detiene el ciclo y se consulta a la persona.

## Review (cuarto gate)

**PASS** sobre `968d912`. Backend: `check`, `makemigrations --check`, 1365 pruebas en PostgreSQL y `bandit` sin incidencias. Frontend: lint, build y `npm audit` sin problemas; Karma 1121 correctas (86,21 % sentencias, 77,95 % ramas). REV-05 a REV-12 verificados como corregidos. Visual verificada en navegador a 390 y 1440 px, claro y oscuro, sobre una base temporal con datos ficticios. Nuevos hallazgos no bloqueantes: [REV-13](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-13.md) (Medium, contraste de `btn-link` en oscuro) y [REV-14](../reviews/REV-2026-11-03-configurar-horarios-y-disponibilidad-14.md) (Low). No verificados: recorrido completo con Tab, error de guardado del diálogo de turno por UI y pausas por UI.

## Corrección de REV-13 y REV-14

Los `btn-link` y la alerta de éxito usan texto claro en tema oscuro; los diálogos definen su borde (ya no usan `.border`, que pisaba el tema); el error de guardado de los diálogos usa `alert alert-danger`. Lint, build y Karma (1121 correctas) pasan. **Pendiente: comprobar en navegador el contraste en oscuro y el nuevo estilo del error.** El gate PASS aplica a `968d912`; esta corrección es posterior.

## Publicación

PR listo para aprobación humana; no se mergea. Toca base de datos (migración aditiva) y un ADR. Limitaciones conocidas: REV-13 y REV-14 abiertos; E2E aplazado hasta el flujo de reserva.
