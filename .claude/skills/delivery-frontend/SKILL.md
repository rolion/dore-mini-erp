---
name: delivery-frontend
description: Implementa una pantalla o flujo a partir de referencias de Google Stitch en el framework y biblioteca UI existentes, conservando contratos y verificando comportamiento y presentación.
disable-model-invocation: true
argument-hint: "[pantalla o especificación a implementar]"
---

Implementa: $ARGUMENTS

Lee docs/design/stitch-workflow.md y aplica su protocolo.

1. Lee la especificación, tokens, screens.md y las instrucciones de implementación del repositorio. Identifica el framework y versiones reales desde sus archivos; no asumas Angular, React ni Tailwind.
2. Recupera por MCP las pantallas registradas y los assets o código disponibles. Usa exportaciones locales existentes si la conexión está bloqueada y explica su procedencia.
3. Identifica componentes reutilizables y cambios necesarios. Si delivery-plan o delivery-engineer ya gobierna el proyecto, respeta su alcance y artefactos; no dupliques sus reglas ni cambies contratos por iniciativa propia.
4. Adapta el diseño a componentes nativos del proyecto. El HTML exportado es referencia: no copies scripts, dependencias externas, CDN, lógica ficticia o estructuras incompatibles.
5. Implementa responsive, temas requeridos, loading, vacío, error, validación y permisos con datos y servicios existentes. No inventes endpoints. Si falta un contrato, informa y limita mocks al entorno permitido por el proyecto.
6. Reutiliza tokens semánticos. Conserva labels, foco, teclado y semántica accesible. Gestiona assets en las rutas y pipeline del proyecto.
7. Ejecuta build, lint y verificaciones relevantes disponibles. Comprueba el flujo crítico; usa Playwright u otra herramienta del proyecto para revisar presentación en los viewports y temas solicitados.
8. Registra en docs/design/implementation.md archivos cambiados, referencias de Stitch, comprobaciones realizadas, desviaciones justificadas y bloqueos.

No rediseñes en Stitch como efecto secundario de implementar. Si hace falta cambiar sustancialmente la referencia, documenta el motivo y solicita una decisión de diseño. No publiques ni hagas deploy sin encargo.

Entrega implementación y evidencia de validación; distingue lo ejecutado de lo pendiente. No invoques otra etapa automáticamente.
