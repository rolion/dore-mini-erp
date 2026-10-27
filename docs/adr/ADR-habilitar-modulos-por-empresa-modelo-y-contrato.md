# ADR-habilitar-modulos-por-empresa-modelo-y-contrato: Módulos habilitados por empresa

**Estado:** Propuesto
**Task relacionado:** TASK-habilitar-modulos-por-empresa
**Fecha:** 2026-10-27

## Contexto
Cada empresa debe elegir qué módulos usa. Hoy todo está siempre disponible. La historia exige selección por empresa, dependencias explícitas, sin instalar código ni ejecutar migraciones por empresa. Los módulos de negocio no importan `accounts` ni entre sí salvo por fachadas (`docs/architecture/ddd.md:819,842`). La API de negocio no se bloquea en esta historia (PB-MOD-004).

## Decisión
1. **Nuevo app Django `modules/modularity`** (infraestructura de configuración, como `accounts`; sin importar módulos de negocio ni `accounts`). Capas mínimas: `domain/` (catálogo estático y reglas puras, sin Django), `application/` (casos de uso), `infrastructure/django/` (modelo y repositorio con `company_id` en el constructor), `api/`.
2. **Catálogo de módulos en código**, inmutable: `key`, `name`, `description`, `is_base`, `requires` (obligatorias), `optional` (integraciones opcionales). Claves: `access` y `catalog` (base); `customers`, `sales`, `expenses`, `reporting`, `purchases`, `inventory`. Mapa: sales→{catalog}, opt {customers}; customers→∅; expenses→∅; reporting→{sales, expenses}, opt {customers}; purchases→{catalog, expenses}; inventory→{catalog}, opt {sales, purchases}. Los módulos base no se persisten: siempre están habilitados.
3. **Persistencia:** tabla `modularity_company_module(id, company_id UUID indexado, module_key, enabled_at)` con unicidad `(company_id, module_key)`. Una fila = módulo no base habilitado. **Sin FK a `accounts_company`** (convención del proyecto). No hay migración de datos: la **primera lectura** de una empresa sin marca de inicialización crea los valores por defecto (`customers`, `sales`, `expenses`, `reporting`) con `bulk_create(ignore_conflicts=True)`. Para distinguir «sin inicializar» de «todo deshabilitado» se guarda además una fila `modularity_company_settings(company_id PK, initialized_at)`; el sembrado ocurre dentro de `transaction.atomic()`.
   - Aplica igual a empresas existentes y nuevas → **la migración solo crea tablas**, sin datos ni lógica por empresa.
4. **Reglas** (dominio puro): habilitar exige todas las `requires` habilitadas (base cuentan como habilitadas); si faltan → conflicto con los nombres faltantes. Deshabilitar un módulo base → error. Deshabilitar exige que ningún módulo habilitado lo tenga en `requires` (se informan los dependientes). Habilitar/deshabilitar es idempotente para el estado ya alcanzado.
5. **Contrato API** (sobre el permiso por defecto `CompanyAdminPermission`; empresa de `company_id_from(request)`):
   - `GET /api/modules/` → `200 [{key, name, description, is_base, enabled, requires:[{key,name,enabled}], optional:[{key,name,enabled}], missing_requires:[nombres]}]`, en orden del catálogo.
   - `POST /api/modules/<key>/enable/` y `/disable/` → `200` con el módulo actualizado; `404` clave desconocida; `409 {detail, missing:[nombres]}` o `{detail, dependents:[nombres]}`; `400` en módulo base.
   - La clave se valida contra el catálogo; la empresa nunca llega del cliente.
6. **Frontend:** un `ModulesService` carga `GET /api/modules/` al iniciar la app autenticada y al cambiar un módulo; el menú (`routes.json` con campo `module`) y un `moduleGuard` (`data.module` en `app.routes.ts`) usan ese estado. Al recargar se vuelve a consultar, por lo que el menú refleja la empresa actual sin cachear en `localStorage`.
7. **No se hace ahora:** permiso 403 por módulo en las vistas de negocio, ni validación de datos al deshabilitar (PB-MOD-004).

## Alternativas consideradas
- **Campo JSON en `Company` (accounts):** menos tablas, pero acopla modularidad a identidad y difícil de consultar/validar. Descartada.
- **Sembrar con migración de datos para cada empresa:** viola «sin migraciones por empresa» y no cubre empresas futuras sin hook en el registro. Descartada.
- **Hook en `register_company_admin`:** acopla accounts con modularity y no cubre empresas existentes. Descartada frente al sembrado en lectura.
- **Incluir `enabled_modules` en la respuesta de login:** evita una llamada, pero queda desactualizado hasta volver a iniciar sesión; no cumple «recargar y aparece». Descartada.
- **Catálogo en BD:** innecesario; los módulos son código del producto.

## Estrategia de rollback / mitigación
Migración solo aditiva (dos tablas nuevas): revertir = `migrate modularity zero` o desplegar la versión anterior; el resto del sistema no depende de ellas, ya que el frontend previo ignora la API. Si la API falla, el frontend muestra todos los ítems base y oculta los opcionales, nunca bloqueando el acceso a la sesión; no hay pérdida de datos de negocio.

## Consecuencias
- Ocultar un módulo no lo protege en la API hasta PB-MOD-004 (riesgo aceptado y documentado).
- Añadir un módulo nuevo al producto = añadir una entrada al catálogo (y su ítem de menú); no requiere migración por empresa.
- La política «defaults al primer uso» significa que cambiar los defaults después solo afecta a empresas aún no inicializadas.
