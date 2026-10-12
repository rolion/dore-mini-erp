---
name: delivery-design-system
description: Define o ajusta tokens, temas y reglas de componentes reutilizables, y genera una pantalla de referencia en Google Stitch para mantener coherencia visual.
disable-model-invocation: true
argument-hint: "[marca, producto o cambio de estilos]"
---

Trabaja sobre: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee el brief disponible, estilos y componentes existentes, assets de marca y decisiones previas. Conserva el sistema existente cuando sea adecuado. No inventes un HEX oficial del logo ni cambies de biblioteca UI sin motivo.
2. Define tokens semánticos: primary, on-primary, background, surface, text, text-muted, border, success, warning, danger y focus. Incluye valores de light/dark cuando corresponda.
3. Define tipografía, escala de tamaños, espaciados, radios, sombras, densidad y breakpoints. Usa fuentes con licencia adecuada verificada; reutiliza la fuente instalada si es apropiada.
4. Especifica variantes y estados de botones, inputs, selectores, tablas, cards, navegación, diálogos, badges y notificaciones que requiere el producto.
5. Escribe docs/design/design-system.md con tabla de tokens y reglas. Incluye un bloque listo para reutilizar en prompts de Stitch con valores explícitos y restricciones.
6. Usa el MCP para generar o actualizar una pantalla de referencia con los componentes principales y los temas requeridos. Aplica los tokens en el prompt; usa capacidades nativas de design system únicamente si están expuestas.
7. Inspecciona el resultado y anota desviaciones respecto a los tokens. Registra los IDs y exportaciones disponibles.

Los tokens del repositorio son la fuente de verdad; no atribuyas a Stitch variables o componentes nativos que no puedas comprobar. No modifiques estilos de producción en esta etapa.

Entrega reglas, referencia visual y discrepancias pendientes. No invoques otra etapa automáticamente.
