---
name: delivery-visual-review
description: Compara la aplicación ejecutada con las referencias de Google Stitch y las especificaciones; revisa coherencia, responsive, temas, estados y accesibilidad, y genera hallazgos con evidencia.
disable-model-invocation: true
argument-hint: "[pantalla o flujo; opcionalmente corregir]"
---

Revisa: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee alcance, especificación, sistema de diseño y registro de pantallas. Recupera por MCP la referencia vigente o utiliza su exportación local identificada.
2. Ejecuta la aplicación con las instrucciones del repositorio y usa la herramienta de navegador disponible. No declares revisión visual si no puedes inspeccionar imágenes de referencia y aplicación.
3. Compara el mismo viewport, tema, estado y datos equivalentes. Comprueba navegación, jerarquía, alineación, tipografía, espaciado, densidad, colores y componentes. Acepta desviaciones justificadas por accesibilidad o biblioteca existente.
4. Revisa desktop/mobile, light/dark y estados relevantes del alcance. Comprueba teclado, foco, labels, contraste y overflow mediante las herramientas disponibles.
5. Documenta cada hallazgo con severidad, pantalla, condiciones de reproducción, esperado, observado, evidencia y acción propuesta. Distingue fallo funcional, desviación visual y mejora opcional.
6. Guarda docs/design/visual-review.md y evidencia sin secretos en docs/design/reviews/<modulo>/.
7. Por defecto solo revisa. Si el usuario pidió corregir, aplica correcciones dentro del alcance y repite las comprobaciones afectadas. No cambies la referencia de Stitch para ocultar una diferencia.

Entrega cobertura real, hallazgos y limitaciones. Usa no verificado cuando falten evidencia o herramientas. No marques aprobado por el usuario ni publiques automáticamente. No invoques otra etapa automáticamente.
