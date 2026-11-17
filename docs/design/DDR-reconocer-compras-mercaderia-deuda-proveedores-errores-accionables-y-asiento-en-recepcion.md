# DDR-reconocer-compras-mercaderia-deuda-proveedores-errores-accionables-y-asiento-en-recepcion: Rechazos accionables y enlace al asiento en la recepción

**Estado:** Propuesto
**Task relacionado:** TASK-reconocer-compras-mercaderia-deuda-proveedores
**Fecha:** 2026-11-17

## Contexto
Al contabilizar la recepción (ADR del mismo task) pueden aparecer rechazos nuevos: configuración de cuentas incompleta, período fiscal cerrado o fecha fuera de períodos. No hay pantallas nuevas; se reutiliza el patrón de alerta accionable de Ventas (`DDR-contabilizar-ventas-cobros-sin-duplicar-errores-accionables-en-detalle-de-pedido.md`) y la plantilla de detalle de `docs/design/design-system.md`.

## Pantallas/flujos afectados
1. **Formulario de recepción** (`features/purchases/pages/reception-form`): al registrar, un 409 `posting_configuration_missing` muestra, sobre el formulario y conservando lo escrito, una alerta con los faltantes (rol/cuenta) y un enlace «Configurar en Compras › Asientos automáticos» (mismo destino que usa Ventas). Un 409 `fiscal_period_unavailable` muestra el mensaje del servidor con la sugerencia de cambiar la fecha de recepción.
2. **Diálogo de reversión de recepción** (`components/receipt-revert-dialog`): los 409 de contabilización (período cerrado) se muestran como error del diálogo, sin cerrarlo ni revertir nada.
3. **Detalle de la recepción** (`pages/reception-detail`): una fila «Asiento contable» en la ficha con fecha, total y enlace al detalle del asiento en Contabilidad cuando existe; sin asiento (sin cobertura o anterior al corte) muestra «Sin asiento contable» en texto tenue. Solo se muestra con el módulo Contabilidad habilitado.

## Componentes/patrones elegidos
Alerta del sistema de diseño en estilo tenue de Contabilidad (contraste AA en claro y oscuro, REV-16 de VEN-01), `app-…` ya existentes de Compras, enlace por `routerLink`. Sin componentes de Oreva nuevos. Todo texto con claves `translate` en es/en/pt (`npm run i18n:check`); los `issues` del servidor se traducen por su `code`/`role` como en Ventas.

## Alternativas consideradas
- Mostrar solo toasts: se pierden al cerrarse y no ofrecen el enlace a la configuración. Descartado.
- Pestaña «Contabilidad» en el detalle de la compra: excesivo para un asiento por recepción. Descartado.

## Comportamiento por privilegio/estado
La persona sin permiso de Contabilidad ve el mensaje del rechazo pero el enlace puede llevarla a una pantalla sin acceso; el backend impone permisos y cobertura (el frontend no es la barrera). Estados: cargando/éxito/error como el resto del formulario; con Contabilidad deshabilitada no aparece nada nuevo.

## Consecuencias
La fila «Asiento contable» es el primer enlace de Compras hacia Contabilidad; si más módulos necesitan lo mismo conviene extraer un componente compartido (deuda aceptada).
