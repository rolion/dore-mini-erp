# ADR-registro-usuarios-empresa-multitenant-propagacion-contexto-empresa: La empresa se deriva de la sesión y viaja explícita hasta cada consulta

**Estado:** Propuesto
**Task relacionado:** TASK-registro-usuarios-empresa-multitenant
**Fecha:** 2026-10-12

## Contexto
Con `company_id` en las tablas (ver `ADR-registro-usuarios-empresa-multitenant-modelo-aislamiento`) hay que decidir **de dónde sale** la empresa de cada operación y **cómo llega** a repositorios, fachadas entre módulos y reportes sin romper los límites de `docs/architecture/ddd.md`.

Hechos del código actual:
- Todos los views instancian repositorios sin argumentos (`catalog/api/views.py:44,52,58,64`, `customers/api/views.py:58,66,76,83`, `sales/api/views.py:87`) y los casos de uso reciben el repositorio por constructor (`catalog/application/commands.py:10-16`).
- Los repositorios consultan `Model.objects` completo (`catalog/.../repositories.py:33-47`, `customers/.../repositories.py:35-59`, `sales/.../repositories.py:39-93`, `expenses/.../repositories.py:42-111`) y `get_for_update` bloquea por pk.
- Las fachadas entre módulos reciben solo ids (`catalog/services.py:20-28`, `customers/services.py:20-36`, `sales/services.py:69-121`, `expenses/services.py:34-51`) y son consumidas por adaptadores construidos sin contexto (`sales/infrastructure/adapters.py:16-32`, `reporting/infrastructure/adapters.py:27-62`); los puertos de aplicación (`sales/application/ports.py`, `reporting/application/ports.py`) no conocen la empresa.
- Regla vigente (`ADR-inicializar-backend-django-modelo-usuario`): los módulos de negocio **no importan `accounts`**; "si necesitan saber quién actúa, reciben un id". `sales/tests/test_boundaries.py` valida el mapa de dependencias entre módulos.
- El requerimiento dice "ajustar las llamadas api para incluir el nombre de empresa y filtrar por ese nombre".

## Decisión
1. **La empresa activa se deriva siempre del usuario autenticado en el servidor** (`request.user.company_id`, resuelto por el token), **nunca** de un dato que envíe el cliente (ruta, query, header ni cuerpo). Las llamadas API **no cambian de forma** (ni rutas, ni payloads): el filtrado "por empresa" se hace en el servidor con la empresa de la sesión. El nombre de la empresa se **devuelve** en la respuesta de login/registro para mostrarse en la UI; no se envía de vuelta.
2. **Cuando el cliente intente apuntar a datos de otra empresa** (p. ej. un UUID ajeno), la respuesta es la misma que para un recurso inexistente (**404**), sin revelar su existencia. Referencias cruzadas inválidas en cuerpos (un `product_id`/`customer_id` de otra empresa en un pedido) se tratan como "no existe" y devuelven el error de validación/no-encontrado actual.
3. **Acceso a la empresa sin importar `accounts`:** un helper mínimo en `shared/` (`shared/tenancy.py`) lee `request.user.company_id` por atributo y falla de forma explícita si falta; los views de los módulos lo usan. No importa modelos de `accounts`, por lo que respeta la regla anterior. No contiene lógica de negocio.
4. **Los repositorios exigen la empresa en el constructor** (`DjangoProductRepository(company_id)`, `DjangoCustomerRepository(company_id)`, `DjangoOrderRepository(company_id)`, `DjangoExpenseRepository(company_id)`, `DjangoExpenseCategoryRepository(company_id)`). Toda consulta (`get`, `get_for_update`, `list`, `find_by_*`, `get_many`, agregados) filtra por `company_id`, y `save` lo establece al crear. No hay forma de construir un repositorio sin empresa. Las entidades de dominio y los casos de uso **no cambian de firma**.
5. **Fachadas entre módulos reciben la empresa como primer argumento** (`get_product_for_sale(company_id, product_id)`, `get_customer_for_sale`, `get_customer_names`, y las funciones de lectura de Sales y Expenses para Reporting). Los **adaptadores** de Sales y Reporting se construyen con `company_id` y lo pasan a las fachadas; así los puertos de aplicación (`ports.py`) permanecen iguales y los casos de uso no se enteran. El mapa de dependencias entre módulos no cambia.
6. **Consultas de lectura (`sales/infrastructure/django/read_queries.py`) y `expenses/services.py`** parten de un queryset ya filtrado por empresa; ninguna función pública de lectura puede invocarse sin `company_id`.
7. **Usuario sin empresa = sin acceso a datos de negocio.** El permiso por defecto de la API exige empresa y rol admin (ver `ADR-registro-usuarios-empresa-multitenant-registro-roles`); un superusuario sin empresa recibe 403 en la API de negocio (sigue usando Django admin).
8. **Guardas automáticas contra olvidos** (parte del contrato de esta decisión, no opcionales):
   - Prueba que recorre los modelos de las apps de negocio y falla si una tabla raíz no tiene `company_id` (salvo una lista explícita de hijas).
   - Prueba de fuga por endpoint: con dos empresas, cada endpoint de listado, detalle y acción devuelve solo los de la propia y 404 sobre ids ajenos.
   - Ampliar `test_boundaries.py` para verificar que ningún módulo de negocio importa `modules.accounts`.

## Alternativas consideradas
- **El cliente envía `company` (nombre o id) y el servidor lo valida:** es literalmente lo pedido ("incluir el nombre de empresa en las llamadas"), pero no agrega ninguna seguridad —el servidor igualmente debe compararlo con la empresa del token— y añade un parámetro que todo servicio del frontend debe recordar enviar, y que un cliente malicioso puede manipular. Se descarta; la intención del requerimiento (que los datos se filtren por la empresa del usuario) se cumple sin él.
- **Nombre de empresa como segmento de URL (`/api/<empresa>/orders/`):** rompe los 7 servicios del frontend y las rutas actuales, duplica la validación contra el token y filtra nombres de empresa en logs. Descartada.
- **Contexto implícito (ContextVar/middleware + manager global auto-filtrado):** no obliga a tocar firmas, pero es global e invisible; falla silenciosamente fuera de una petición (comandos, tests, shell) y oculta qué consultas están filtradas. Se prefiere explícito y comprobable.
- **Pasar `company_id` a cada método de repositorio/caso de uso:** explícito, pero ensucia todas las firmas y los puertos y es fácil de omitir en una llamada. El constructor lo exige una sola vez por petición.
- **Poner la empresa en las entidades de dominio:** contamina el dominio con una preocupación de infraestructura; no aporta reglas de negocio.

## Estrategia de rollback / mitigación
- El cambio de firmas es interno al backend; el **contrato HTTP no cambia** (salvo campos aditivos en login/registro), por lo que el frontend actual sigue funcionando sin cambios para las pantallas existentes.
- Rollback por reversión del PR junto con las migraciones del ADR de aislamiento. No hay estado de transición con código a medias porque el filtrado y el relleno salen juntos.
- Mitigación de fuga: las pruebas de fuga y de modelos (decisión 8) se ejecutan en CI local (`python manage.py test`); un endpoint nuevo sin filtro por empresa debe hacer fallar una prueba antes de llegar a producción.
- Si se detecta una fuga en producción: el interruptor operativo es desactivar el registro (ver ADR de registro y roles) y revocar tokens (`Token.objects.all().delete()`) mientras se corrige.

## Consecuencias
- Fácil: casos de uso y dominio intactos; el frontend no cambia sus llamadas; cada nuevo repositorio tiene el patrón obvio a copiar.
- Difícil: el filtro es responsabilidad de cada repositorio; un repositorio nuevo escrito sin `company_id` es un riesgo, mitigado por las pruebas del punto 8 pero no imposible.
- Deuda aceptada: sin RLS ni manager global, la protección es de aplicación; los tokens de DRF siguen sin expirar (ya aceptado en `ADR-frontend-login-backend-autenticacion-token`) y el token identifica a la empresa solo por la fila del usuario, por lo que un cambio de empresa de un usuario aplica de inmediato.
- Los tests existentes (`fakes.py`, `test_repository.py`, `test_api.py` de cada módulo) deben ajustarse a los constructores nuevos; el plan lo dimensiona.
