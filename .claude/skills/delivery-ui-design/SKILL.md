---
name: delivery-ui-design
description: Genera y refina pantallas de producto en Google Stitch usando el brief UX, el sistema de diseño y los componentes del proyecto; documenta estados y especificaciones para implementación.
disable-model-invocation: true
argument-hint: "[pantalla o flujo, temas y dispositivos]"
---

Diseña: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee ux-brief.md y design-system.md si existen, requisitos y pantallas relacionadas. Si faltan, completa un brief mínimo y registra supuestos; no bloquees un cambio pequeño por documentación opcional.
2. Revisa el frontend: biblioteca de componentes, navegación, tablas y formularios existentes. Diseña dentro de sus capacidades o identifica explícitamente lo que requiere un componente nuevo.
3. Prepara el prompt de Stitch: objetivo, usuario, flujo, jerarquía, textos en el idioma del producto, datos ficticios, componentes, tokens exactos, tema y dispositivo. Define lo que debe conservarse de la pantalla existente.
4. Usa las herramientas expuestas para generar o editar en el proyecto registrado. No sustituyas el uso de Stitch por una descripción textual sin indicar el bloqueo.
5. Inspecciona el resultado visual. Revisa acción principal, legibilidad, densidad, consistencia, responsive y estados. Refina con cambios concretos, manteniendo las partes que funcionan.
6. Genera referencias desktop/mobile y light/dark según el alcance. Describe los estados restantes en la especificación si no necesitan una generación independiente.
7. Actualiza screens.md y exporta lo disponible. Guarda docs/design/specs/<modulo>-<pantalla>.md con layout, componentes, interacciones, validación, permisos, estados y criterios de aceptación.

No modifiques código de producción ni supongas aprobación del usuario. No agregues reglas de negocio a partir de detalles decorativos generados por Stitch.

Entrega las referencias reales, especificación y estado de revisión. No invoques otra etapa automáticamente.
