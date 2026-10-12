# ADR-registro-usuarios-empresa-multitenant-modelo-aislamiento: Aislamiento de datos por empresa con columna `company_id` en un único esquema

**Estado:** Propuesto
**Task relacionado:** TASK-registro-usuarios-empresa-multitenant
**Fecha:** 2026-10-12

## Contexto
Hoy todos los datos de negocio son globales: ninguna de las tablas de `catalog`, `customers`, `sales` y `expenses` tiene propietario (`ProductModel`, `CustomerModel`, `OrderModel`/`OrderItemModel`/`PaymentModel`, `ExpenseCategoryModel`/`ExpenseModel`), y `reporting` no tiene modelos. El requerimiento pide que cada usuario vea y modifique **solo** los datos de su empresa.

Restricciones relevantes ya establecidas:
- `docs/architecture/ddd.md:1253` y `CLAUDE.md`: "Multiempresa compleja" está fuera del MVP. Lo pedido es la forma simple: **una empresa por usuario, sin jerarquías ni usuarios en varias empresas**.
- Los módulos referencian a otros solo por UUID, sin FK (`sales/infrastructure/django/models.py:9-10`), y no se importan modelos entre sí.
- `CLAUDE.md`: nunca editar una migración aplicada; `makemigrations` nuevo por cambio.
- Hay datos de desarrollo posibles en las tablas actuales; el proyecto está en construcción.
- Decisión de negocio tomada por el usuario en esta etapa: el registro público **solo crea empresas nuevas**; un nombre de empresa existente se rechaza y los usuarios adicionales de una empresa los agrega su admin.

## Decisión
1. **Un solo esquema y una sola base; discriminador `company_id` (UUID) en cada tabla raíz de negocio:** `catalog_product`, `customers_customer`, `sales_order`, `expenses_category`, `expenses_expense`. Las tablas hijas (`sales_order_item`, `sales_payment`) heredan la empresa de su pedido por la FK interna de Sales y **no** llevan columna propia (se consultan siempre a través del pedido).
2. **Sin FK entre módulos:** `company_id` en las tablas de negocio es un `UUIDField` con índice, igual que las demás referencias entre módulos. La entidad `Company` vive en `accounts` (ver ADR de registro y roles).
3. **Columna obligatoria (`NOT NULL`) tras migrar los datos existentes.** Cada app de negocio recibe una migración propia nueva (nullable → relleno → `NOT NULL`), sin editar migraciones aplicadas.
4. **Empresa por defecto para datos existentes:** `accounts` crea una `Company` con un UUID **fijo y conocido** (constante literal copiada en cada migración, para que las migraciones queden congeladas y las apps de negocio no dependan de `accounts`). Los usuarios y filas existentes se asignan a ella. Se renombra luego por el admin de Django. En una base vacía queda una empresa sin uso, inocua.
5. **Unicidades que pasan a ser por empresa:**
   - Categoría de gasto: `UniqueConstraint(Lower('name'))` global (`expenses/infrastructure/django/models.py:19-21`) → `UniqueConstraint('company_id', Lower('name'))`.
   - Teléfono duplicado de clientes (`customers/.../repositories.py:55-59`, advertencia, no restricción): se limita a la empresa.
   - `sales_item_unique_product_per_order` ya es por pedido; no cambia.
6. **Los agregados de dominio no cambian:** `company_id` es una preocupación de persistencia y de la capa de aplicación/infraestructura; las entidades (`Product`, `Customer`, `Order`, `Expense`…) no lo conocen, de modo que el dominio sigue sin importar Django ni tenancy.
7. **Índices:** `company_id` indexado; los índices compuestos de consultas frecuentes (`company_id` + fecha/estado) se evalúan en el plan con los filtros reales de `sales/api/filters.py` y `expenses/api/filters.py`, no se anticipan aquí.

## Alternativas consideradas
- **Esquema por empresa (p. ej. `django-tenants`):** aislamiento fuerte, pero agrega dependencia, migraciones por esquema, enrutamiento por dominio/subdominio y complica reportes y tests; desproporcionado para una empresa por usuario y sin requerimiento de aislamiento físico.
- **Base de datos por empresa:** el máximo aislamiento, y el mayor costo operativo (conexiones, migraciones, backups). Descartada.
- **Discriminador con librería (`django-multitenant`) o manager global auto-filtrado por hilo:** menos riesgo de olvidar un filtro, pero es magia implícita (estado global por hilo/ContextVar), complica `shell`, tareas y tests, y exige nueva dependencia (hay que avisar según `CLAUDE.md`). Se prefiere el filtrado explícito (ver ADR de propagación) respaldado por pruebas.
- **Row Level Security de PostgreSQL:** defensa en profundidad atractiva (la BD impide fugas aunque falle el código), pero exige fijar una variable de sesión por transacción y políticas por tabla, y se mezcla mal con conexiones agrupadas. Se difiere: es una mejora posible sobre este mismo modelo si el riesgo lo justifica.
- **FK real `company` en las tablas de negocio:** integridad referencial, pero acopla las migraciones de cada módulo a `accounts` y rompe la convención de "solo UUID". Descartada; el costo es que una empresa borrada dejaría filas huérfanas, por eso las empresas **no se borran físicamente** (se desactivan).
- **Empresa por defecto creada solo si hay datos:** evita una fila inútil en bases vacías, pero deja filas huérfanas si hay datos de negocio sin usuarios. Se prefiere la regla única y determinista.

## Estrategia de rollback / mitigación
- **Aditivo y reversible:** cada migración agrega una columna e índices; el rollback (`migrate <app> <anterior>`) las elimina. El relleno es `RunPython` con reversa vacía (la columna desaparece). Se pierde únicamente la asignación a empresa, no los datos de negocio. En las constraints de categoría, el rollback restaura la unicidad global; **puede fallar** si ya hay dos empresas con la misma categoría: en ese caso la reversa debe primero renombrar o fusionar manualmente (anotado como paso de runbook en el plan).
- **Antes de aplicar en un entorno con datos reales:** respaldo de la base (`pg_dump`). Probar `migrate` y `migrate` hacia atrás sobre una copia.
- **Orden de despliegue:** primero las migraciones de `accounts` (empresa por defecto) y luego las de las apps de negocio; el código nuevo y las migraciones salen juntos (no hay fase mixta con código viejo y columna `NOT NULL`, porque el relleno ocurre en la misma migración).
- **Verificación post-migración:** conteo de filas sin `company_id` = 0 y conteo por empresa = totales previos.

## Consecuencias
- Fácil: un solo despliegue, un solo conjunto de migraciones, reportes y consultas SQL como hoy con un filtro adicional.
- Difícil: el aislamiento depende de que **toda** consulta incluya el filtro; se mitiga con el ADR de propagación (repositorios con empresa obligatoria en el constructor) y pruebas de fuga por endpoint.
- Deuda aceptada: sin FK ni RLS, la BD no impide por sí sola una fila con `company_id` inexistente o cruzada; no hay un solo usuario en varias empresas ni transferencia de datos entre empresas; renombrar empresa y fusionarlas quedan fuera.
- `docs/architecture/ddd.md` debe actualizarse (el plan lo incluye) para registrar que existe "multiempresa simple" (discriminador por columna) y que "multiempresa compleja" sigue fuera de alcance.
