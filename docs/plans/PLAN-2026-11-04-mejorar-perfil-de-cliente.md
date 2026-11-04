# PLAN-2026-11-04-mejorar-perfil-de-cliente (v1)

**Task:** TASK-mejorar-perfil-de-cliente · **Modo:** COMPLETO · **Specification readiness:** READY
**DDRs / ADRs:** DDR-mejorar-perfil-de-cliente-perfil-accionable · ADR-clientes-mvp-historial-compras (vigente, sin cambios)

## Objective
Convertir el perfil del cliente en una pantalla de trabajo: contacto accionable, resumen de compras (última compra, pedidos, total comprado, saldo pendiente), historial con código, pagado, saldo y estados, y acciones claras. Solo frontend; sin cambios de API ni de datos.

## Context
Ver TASK (Investigación). El backend ya devuelve `code`, `paid_total` y `balance` en `GET /api/orders/?customer_id=…`; el frontend los descarta.

# Specification

## Domain context
Bounded context Customers (perfil) que consume el contrato HTTP de Sales (ADR historial-compras); Customers no importa Sales en backend. En el frontend solo se reutilizan badges y modelos de estado de Sales (precedente: Reporting).

## Ubiquitous language
| Término | Significado | Fuente |
|---|---|---|
| Total comprado | Suma de `total` de pedidos no cancelados del cliente | Regla de pedido válido, `read_queries.py:17-20` |
| Saldo pendiente | Suma de `balance` de pedidos no cancelados | `OrderSummarySerializer` `balance` |
| Última compra | Fecha del pedido no cancelado más reciente | Orden `-order_date` por defecto |
| Pedido | Orden de venta; se identifica por `code` | `serializers.py:64-68` |

## Current behavior
Ver TASK: detalle con `dl.row` de 7 filas, botones al pie, tabla con Fecha/Total/Estado/Pago en texto (`customer-purchase-history.component.html:11-31`).

## Expected behavior
Según el DDR: tarjeta de identidad con acciones en la cabecera, contacto con enlaces, tira de 4 cifras, historial enriquecido, pie de auditoría, estados vacío/error/parcial/inactivo y vista móvil.

## Domain rules / invariants
- **INV-01 (nueva, financiera):** los agregados excluyen pedidos `CANCELLED` (misma regla que Reporting) y se calculan sin `float`: enteros en la unidad mínima a partir de las cadenas decimales de la API; el resultado se formatea con el pipe `money`.
- **INV-02:** el frontend no reinterpreta reglas de estado: muestra `status`/`payment_status` tal como llegan; un código desconocido se muestra como texto.
- **INV-03 (existente):** historial visible también para clientes inactivos.

## Acceptance criteria
- **AC-01** El encabezado muestra nombre, badge Activo/Inactivo y las acciones Nuevo pedido (primaria), Editar, Activar/Desactivar; no hay botón Volver ni fila «Nombre».
- **AC-02** El teléfono es un enlace `tel:` y hay un botón «WhatsApp» con `https://wa.me/<solo dígitos>`; el correo es `mailto:`; sin dato se lee «Sin teléfono» / «Sin correo».
- **AC-03** Con datos cargados se muestran Última compra, Pedidos, Total comprado y Saldo pendiente calculados según INV-01; sin pedidos: «Sin compras», 0, `Bs 0.00`, `Bs 0.00`; durante carga o error no se muestran cifras (no 0).
- **AC-04** La tabla muestra Pedido (código enlazado a `/pocketbiz/sales/orders/:id`), Fecha, Total, Pagado, Saldo, Entrega y Pago con badges; cancelados atenuados con saldo «—».
- **AC-05** «Ver todos los pedidos» lleva a la lista de pedidos filtrada por el cliente; el pie dice «Mostrando X de Y pedidos» y, si Y > X, las cifras avisan «Calculado con los X pedidos más recientes».
- **AC-06** Sin pedidos: mensaje «Este cliente aún no tiene pedidos.» y botón «Crear primer pedido».
- **AC-07** «Nuevo pedido» / «Crear primer pedido» abren el formulario de pedido con el cliente preseleccionado; no se muestran si el cliente está inactivo o el módulo Pedidos está deshabilitado.
- **AC-08** «Creado/Actualizado» aparece como pie discreto, no como filas de la ficha.
- **AC-09** En <576 px la tabla se apila, las cifras van 2×2 y las acciones se reparten en varias líneas; tabla con `<caption>` oculta y `scope="col"`; botones/enlaces de solo icono con `aria-label` y `title`.
- **AC-10** Todo texto visible usa claves en es/en/pt (mismas claves) y `npm run i18n:check` pasa.

## Edge cases / Error cases
- **EDGE-01** Error del historial: mensaje visible, acciones y datos del perfil intactos, sin cifras.
- **EDGE-02** Todos los pedidos cancelados: cifras en 0 / «Sin compras», la tabla los lista atenuados.
- **EDGE-03** Teléfono con símbolos/espacios: el enlace `wa.me` usa solo los dígitos.
- **EDGE-04** Cliente con más de 100 pedidos: aviso de cifras parciales.
- **EDGE-05** Pedido con código de estado desconocido: se muestra el código como texto.

## Authorization / permissions
Sin cambios: el backend sigue filtrando por empresa y respondiendo 403; el frontend no es barrera.

## API contract
Sin cambios de backend. **API-01:** el servicio del frontend pasa a leer también `code`, `paid_total`, `balance` del contrato ya existente (compatible hacia atrás).

## UI behavior
**UI-01** Plantilla Detalle (`design-system.md` §5) adaptada según DDR. **UI-02** Cifras con `app-report-card` (§5 Dashboard). **UI-03** Badges con `app-order-status-badge` / `app-payment-status-badge` (§3). **UI-04** Dinero con pipe `money`, alineado a la derecha. **UI-05** Estados cargando/vacío/error/parcial/inactivo según DDR.

## Non-functional requirements
Sin nuevas dependencias; sin `any`; suscripciones con `takeUntilDestroyed`; accesibilidad AA (texto con estados, objetivos ≥ 44 px en móvil).

## Out of scope
Backend o agregados en servidor; paginación o filtros dentro del perfil; gráficos; tiempo relativo («hace N días»); cambiar el patrón de otros detalles; avatar del cliente.

## Open questions
- Si «Reembolsado» debe excluirse de Total comprado: se mantiene la regla de Reporting (solo cancelados). Revisable más adelante sin cambio de contrato.

# Test Specification

## Unit tests
- Utilidad de suma decimal (INV-01): sumas exactas (`0.1 + 0.2`), cadenas vacías, valores grandes.
- Cálculo de resumen: excluye cancelados, fecha más reciente, lista vacía, todo cancelado (AC-03, EDGE-02).
- Enlace de WhatsApp: normalización de dígitos (AC-02, EDGE-03).

## Integration tests (componentes, `provideTestTranslations()`)
- `customer-detail`: encabezado y acciones, activo/inactivo, enlaces de contacto, textos «Sin …» (AC-01, AC-02, AC-07, AC-08).
- `customer-purchase-history`: columnas, badges, cancelados, pie «Mostrando X de Y», aviso parcial, vacío, error, cargando (AC-03 a AC-06, EDGE-01, EDGE-04, EDGE-05).
- `customer-orders-api.service`: mapea `code`, `paid_total`, `balance`.
- `order-form`: preselección de cliente por query params en alta; ignorada en edición (AC-07).
- Prueba de paridad de claves i18n + `npm run i18n:check` (AC-10).

## E2E
**NO** — no es un flujo crítico de extremo a extremo; no justifica instalar Playwright.

## Regression tests
Las pruebas existentes de `customer-detail`, `customer-purchase-history`, `order-form` y `order-list` deben seguir en verde.

## Acceptance criteria mapping
| AC | Verification |
|---|---|
| AC-01, AC-08 | Prueba de componente `customer-detail` |
| AC-02 | Prueba de componente + unidad del enlace de WhatsApp |
| AC-03 | Unidad del resumen + prueba de componente del historial |
| AC-04, AC-06 | Prueba de componente del historial |
| AC-05 | Prueba de componente del historial |
| AC-07 | Pruebas de `customer-detail` y `order-form` |
| AC-09 | Prueba de marcado (caption, `scope`, `aria-label`) + revisión visual manual en móvil |
| AC-10 | `npm run i18n:check` + prueba de paridad de claves |

# Implementation Plan

## Architecture considerations
Lógica no visual en funciones/servicios puros (`customer-purchase-summary.ts`); componentes presentacionales con `input()`. El historial sigue recibiendo los pedidos desde la página (sin peticiones propias).

## Proposed solution
Ampliar el modelo y el servicio con `code`, `paidTotal`, `balance`; derivar el resumen con una función pura; rehacer las plantillas de detalle e historial según el DDR; añadir prefill por query params al alta de pedido.

## Files/components affected
- Frontend `features/customers`: `models/customer.ts`, `services/customer-orders-api.service.ts` (+spec), nuevo `models/customer-purchase-summary.ts` (+spec), `pages/customer-detail/*` (html, ts, spec), `components/customer-purchase-history/*` (html, ts, spec).
- Frontend `shared/`: utilidad de suma decimal (`shared/utils/decimal-sum.ts` + spec).
- Frontend `features/sales/pages/order-form`: leer `customer` y `customer_name` en alta (+spec).
- i18n: `assets/i18n/{es,en,pt}.json`.
- Docs: `docs/design/design-system.md` solo si el patrón de acción primaria se adopta como estándar (no en este PR salvo decisión en review).
- Backend: ninguno. Migraciones: ninguna.

## Implementation steps
1. Utilidad de suma decimal sin `float` y pruebas (INV-01).
2. Ampliar `CustomerOrderSummary` y el servicio (API-01); actualizar pruebas existentes.
3. Función pura de resumen (última compra, conteo, total, saldo; excluye cancelados) y pruebas (AC-03, EDGE-02).
4. Rehacer el historial: columnas, badges (con guarda de tipo para códigos desconocidos, EDGE-05), cancelados, pie, aviso parcial, vacío con CTA, tabla apilada y accesibilidad (AC-04 a AC-06, AC-09).
5. Rehacer el detalle: cabecera con acciones, contacto accionable, tira de cifras con `app-report-card`, pie de auditoría, ocultar acciones según inactivo/módulo (AC-01, AC-02, AC-03, AC-07, AC-08).
6. Prefill del cliente en el alta de pedido por query params (AC-07).
7. Claves i18n es/en/pt y `npm run i18n:check`, `npm run lint`, `npm test`, `npm run build` (AC-10).
8. Revisión visual manual en escritorio y móvil, claro y oscuro.

## Database / migrations
No aplica.

## Risks
- Agregados parciales con > 100 pedidos: mitigado con aviso explícito.
- Los badges de Sales exigen tipos `OrderStatus`/`PaymentStatus`: se resuelve con guarda de tipo en el historial y texto plano para códigos desconocidos.
- `app-report-card` vive en Reporting: reutilizar sin copiar; si molesta el acoplamiento, moverlo a `shared/` en este mismo PR (regla del sistema de diseño).
- Cómo detectar el módulo Pedidos deshabilitado (`ModulesService`): confirmar en build con el patrón de `order-form.component.ts:89-92`.

## New dependencies
Ninguna.
