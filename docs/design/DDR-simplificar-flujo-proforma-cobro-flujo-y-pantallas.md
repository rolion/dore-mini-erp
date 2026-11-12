# DDR-simplificar-flujo-proforma-cobro-flujo-y-pantallas: Flujo corto de aceptación y cobro en contexto

**Estado:** Propuesto (reemplaza parcialmente `DDR-presentar-aceptar-versionar-proformas-detalle-decisiones-e-impresion` en el diálogo de decisión, y `DDR-cobrar-servicios-anticipos-pagos-parciales-pantallas-cobros` en el formulario de pago)
**Task relacionado:** TASK-simplificar-flujo-proforma-cobro
**Fecha:** 2026-11-12

## Contexto
Hoy aceptar y cobrar un caso simple exige unas 14 interacciones: presentar (con confirmación) → marcar casillas → «Aceptar seleccionadas» → formulario → «Revisar resumen» → «Confirmar» → botón «Cobrar» (cambia de módulo) → «Registrar pago» → monto → «Repartir en orden» → «Revisar resumen» → «Confirmar cobro». Objetivo: bajar a 6-7 (presentar, aceptar todo, cobrar ahora, confirmar), sin perder trazabilidad ni las confirmaciones de acciones irreversibles.

## Pantallas/flujos afectados
1. **Detalle de proforma** (genérica y odontológica): barra de acciones, sección de tratamientos y diálogo de decisión.
2. **Diálogo de cobro** (componente compartido nuevo): se abre desde la proforma, desde el éxito de la aceptación, desde la fila de la ficha del paciente y desde el detalle de Cobros.
3. **Ficha del paciente → tarjeta Proformas**: columnas Aceptado / Cobrado / Saldo y acción «Cobrar».
4. **Detalle de Cobros** y lista de Cobros: navegación de regreso y etiquetas.
5. **Menú lateral** y **badges de estado** (transversal a estas pantallas).

## Componentes/patrones elegidos
- **Detalle con selección de líneas** (`design-system.md` §5, referencia `proforma-detail` / `dental-proforma-detail`), con estos ajustes:
  - Barra de líneas: **«Aceptar todo»** (primario cuando hay pendientes), «Aceptar seleccionadas», «Rechazar seleccionadas», «Imprimir». «Aceptar todo» abre el diálogo con todas las pendientes elegidas.
  - **Diálogo de decisión de un solo paso** (`NgbModal`/`dialog` actual): arriba el resumen en una frase («oscar acepta 2 tratamientos por Bs 300.00» + lista), debajo los campos y un único «Confirmar» con el aviso de irreversibilidad. Al aceptar: *quién acepta* (precargado) y *medio*; **Referencia/evidencia** dentro de un `<details>` («Más datos»). El **motivo solo al rechazar y al rectificar** (obligatorio al rectificar como hoy). Rectificar conserva su diálogo.
  - *Quién acepta* precargado: paciente menor de edad con responsable → el **responsable**; en otro caso el nombre del paciente/cliente; siempre editable.
  - Éxito de la aceptación: `alert-success` con CTA primario **«Cobrar ahora (Bs X)»** y «Más tarde»; solo si la proforma es cobrable y el módulo Cobros está habilitado.
- **Diálogo de cobro** (nuevo, `shared/components/payment-dialog/`, patrón de `purchase-payments-tab`, §5): encabezado con saldo; campo **Monto** con atajos `Total Bs X` · `50 %` · `Otro` (foco al campo); fecha (hoy, máx. hoy), método (Efectivo por defecto), referencia; una línea «Se aplicará a: A Bs …, B Bs …» (**reparto automático en orden**); enlace plegado **«Distribuir por tratamiento»** que muestra la tabla de imputaciones editable; un solo **«Confirmar cobro»** (sin paso de resumen aparte), clave de idempotencia al abrir, datos conservados ante errores, recarga y reconstrucción de la distribución tras un 409.
- **Estado de cobro en la proforma**: en el `dl` de totales, junto a Propuesto/Aceptado/Pendiente de decisión se muestran **Cobrado** y **Saldo** (si Cobros está habilitado); desaparece la nota «El saldo de cobro no se calcula aquí». El botón **«Cobrar»** del encabezado abre el diálogo (ya no navega) y es el botón primario cuando hay saldo.
- **Ficha del paciente**: tabla con columnas *Aceptado · Cobrado · Saldo* (con Cobros habilitado) y acción **«Cobrar»** por fila (abre el diálogo). Los datos de cobro salen de `GET /api/receivables/obligations/?customer_id=` unidos por número; sin obligación, Cobrado = 0.00 y Saldo = Aceptado.
- **Detalle de Cobros** (plantilla Detalle sin cambios de estructura): botón **«Volver a la proforma»** (con `proforma_id`) y, en dental, «Volver al paciente»; «Registrar pago» abre el mismo diálogo compartido; la tabla de pagos y las tarjetas de importes se mantienen.
- **Badge de estado compartido** `app-status-badge` (`shared/components/status-badge/`): icono + fondo tintado + texto, tonos `success|warning|danger|info|muted`, contraste ≥ 4.5:1 en tema claro y oscuro con las variables de `_variable.scss` (sin HEX). Se aplica a decisión de línea, aceptación de la proforma y estado de cobro. Se propone la actualización de `design-system.md` §3 (nueva fila y nota: los badges de estas pantallas usan `app-status-badge`; el resto migra al tocarse).
- **Etiquetas**: decisión → «Sin decidir / Aceptada / Rechazada»; aceptación de la proforma → «Sin decidir / Parcialmente aceptada / Aceptada / Rechazada»; cobro → «Por cobrar / Parcial / Pagado». En contexto Odontología se dice «Paciente»; en Cobros genérico «Cliente», salvo que el compromiso sea dental (el detalle recibe el tipo y usa «Paciente»). Importes siempre con dos decimales. «Autorizada para el trabajo» → «Aprobada para realizar».
- **Menú**: «Cobros» como ítem plano (`/pocketbiz/receivables`, módulo `receivables`, sin submenú).

## Alternativas consideradas
- **Mantener el cobro como pantalla separada** y solo recortar pasos: no resuelve el cambio de contexto ni el CTA tras aceptar; descartada.
- **Cobrar automáticamente al aceptar:** mezcla dos decisiones de negocio y dinero sin confirmación explícita; descartada.
- **Reparto proporcional por defecto:** menos predecible para caja y más difícil de explicar; se elige «en orden».
- **Panel lateral en vez de diálogo:** más espacio para la distribución avanzada, pero un patrón nuevo; se mantiene el diálogo del sistema.
- **Mover todos los badges del sistema a `app-status-badge`:** fuera de alcance; se aplica solo a estas pantallas.

## Comportamiento por privilegio/estado
- Estados del diálogo de cobro: cargando saldo, error con «Reintentar» y datos conservados, éxito con comprobante `CB-NNNNNN` y saldo actualizado; botón deshabilitado mientras guarda; foco al abrir (monto) y al cerrar (botón que lo abrió); `aria-label` en cada importe de imputación; atajos como botones con `aria-pressed`.
- «Cobrar» y las columnas de cobro solo aparecen si el módulo `receivables` está habilitado y la proforma es cobrable (`collectible`); sin saldo no se ofrece cobrar.
- Sin permiso o módulo deshabilitado: el backend responde 403 y la UI lo muestra; el frontend no es la barrera de seguridad (valida el servidor: líneas aceptadas, saldos, idempotencia, módulos por fuente).

## Consecuencias
- Los textos de estado cambian en varias pantallas y pruebas; las capturas de la documentación quedan desactualizadas.
- Coexisten dos estilos de badge hasta que el resto de pantallas migre (deuda visual aceptada).
- Cobros sigue siendo genérico: Odontología y Cotizaciones solo consumen el diálogo compartido.
- Sin anulación de pagos ni profesional por línea (fuera de alcance, igual que PB-COB-001).
