---
name: delivery-ux-research
description: Define necesidades, flujos, arquitectura de información y criterios UX antes de diseñar pantallas. Usa referencias existentes de Google Stitch cuando estén disponibles.
disable-model-invocation: true
argument-hint: "[producto o módulo y objetivo]"
---

Trabaja sobre: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Revisa los requisitos, pantallas existentes, rutas, roles y restricciones del alcance. Si hay referencias de Stitch, recupéralas mediante lectura para entender el flujo actual.
2. Define usuarios, tarea principal, resultado esperado y problemas que el flujo debe resolver. Etiqueta las hipótesis; no presentes inferencias como investigación de usuarios realizada.
3. Diseña la arquitectura de información: secciones, navegación, entradas y salidas. Define flujo principal, alternativas, errores y restricciones por rol.
4. Para cada pantalla, especifica propósito, datos, acción principal, acciones secundarias, estados y criterios verificables de aceptación.
5. Formula preguntas pendientes y separa cuáles bloquean el diseño. Resuelve detalles menores con supuestos explícitos; pregunta solo cuando una decisión material no puede inferirse.
6. Guarda o actualiza docs/design/ux-brief.md con contexto, evidencia, hipótesis, flujos, pantallas, criterios y preguntas.

No generes pantallas nuevas en esta etapa ni modifiques código. Stitch aporta referencias visuales; no sustituye entrevistas ni valida necesidades de usuarios.

Entrega el brief y el alcance listo para delivery-design-system o delivery-ui-design. No invoques otra etapa automáticamente.
