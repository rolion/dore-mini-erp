# DDR-bloquear-api-modulos-deshabilitados-integraciones-opcionales-ui: Pantallas de módulos activos con Clientes deshabilitado

**Estado:** Propuesto
**Task relacionado:** TASK-bloquear-api-modulos-deshabilitados
**Fecha:** 2026-10-27
**Complementa a:** DDR-bloquear-api-modulos-deshabilitados-pantalla-no-habilitado (no lo reemplaza)

## Contexto
REV-01 (High): con Clientes deshabilitado, Pedidos (lista y formulario) y Reportes siguen habilitados pero piden datos de Clientes al abrirse. La API responde 403 `module_disabled` y el interceptor lleva a «Módulo no habilitado», así que esas pantallas quedan inutilizables desde la UI aunque la API funcione (AC-07, AC-08).

## Pantallas/flujos afectados
- Lista de pedidos: el filtro por cliente.
- Formulario de pedido: el selector de cliente y la creación rápida de cliente.
- Reportes: la tarjeta «Top clientes».
- Servicio de búsqueda de clientes (`CustomerOptionsService`).

## Componentes/patrones elegidos
- Regla general: una pantalla de un módulo habilitado **no pide datos de una integración opcional deshabilitada**. La decisión sale de `ModulesService.enabledKeys$`, que `moduleGuard` ya deja cargado antes de activar cualquier ruta con módulo.
- Con Clientes deshabilitado, esos controles/tarjeta **no se muestran** (sin mensaje de error ni tabla vacía engañosa). Los pedidos ya vinculados siguen mostrándose sin cliente (la API devuelve `customer: null`).
- `CustomerOptionsService.search` devuelve una lista vacía **sin hacer la petición** como segunda defensa.
- El interceptor no cambia: un 403 `module_disabled` inesperado sigue llevando a «Módulo no habilitado» (AC-10).

## Alternativas consideradas
- Que el interceptor navegue solo si el módulo rechazado es el de la ruta actual: cambia el alcance de AC-10 (requiere aprobación) y oculta peticiones indebidas; descartada.
- Dejar los controles visibles y vacíos: se ven operables pero la API los rechaza (400 al asignar); descartada.

## Comportamiento por privilegio/estado
- Estados: se agrega solo «módulo opcional no habilitado» = el control no existe. Al habilitar Clientes y recargar, vuelven los controles.
- El frontend no es la barrera: la API rechaza asignar o filtrar por cliente (400) y `top-customers` (403).

## Consecuencias
Se adelanta una parte pequeña de PB-MOD-003 (ocultar campos y tarjetas de módulos ausentes) solo para Clientes en Pedidos y Reportes; el resto de PB-MOD-003 (Inventario, contadores) sigue pendiente.
