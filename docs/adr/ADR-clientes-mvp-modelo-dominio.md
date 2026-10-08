# ADR-clientes-mvp-modelo-dominio: Módulo `customers`, entidad Customer, normalización de teléfono y persistencia

**Estado:** Propuesto
**Task relacionado:** TASK-clientes-mvp
**Fecha:** 2026-10-08

## Contexto
`catalog` ya fijó el patrón del primer bounded context de negocio (ver `ADR-catalogo-productos-mvp-modelo-dominio`): entidad de dominio pura, casos de uso, `Protocol` de repositorio, modelo Django + mapper en infraestructura, UUID, errores de validación por campo. `docs/architecture/ddd.md:228-309` define Customers: `Customer(id, name, phone, email, notes, created_at, updated_at)`, Value Objects `PhoneNumber` (ejemplo `+591 7xxxxxxx`) y `EmailAddress`, reglas (puede existir sin email; el teléfono es un identificador práctico; no eliminar con historial; preferir desactivar) y casos de uso `CreateCustomer/UpdateCustomer/DeactivateCustomer`, `GetCustomer/SearchCustomers/ListCustomers`. `backend/requirements/base.txt` no tiene librería de teléfonos y `CLAUDE.md` exige avisar antes de instalar dependencias. REQ-CUS-001/006 piden teléfono normalizado "cuando sea posible" y comparar duplicados por teléfono normalizado sin bloquear necesariamente.

## Decisión
- **Nuevo módulo** `backend/modules/customers/` (app `modules.customers`, label `customers`), registrado en `INSTALLED_APPS`, con las mismas capas y la misma forma que `catalog`, creadas solo con contenido real:
  - `domain/`: entidad `Customer` (dataclass sin Django) con `create`, `rename`, `change_contact` (teléfono, correo), `change_notes`, `activate`, `deactivate` (idempotentes); `CustomerValidationError` (errores por campo) y `CustomerNotFound`; `CustomerRepository` como `Protocol`; funciones puras de validación y de normalización de teléfono.
  - `application/`: commands `CreateCustomer`, `UpdateCustomer`, `ActivateCustomer`, `DeactivateCustomer`; queries `GetCustomer`, `ListCustomers` (con búsqueda y filtro de estado; `SearchCustomers` es `ListCustomers(search=...)`, no un caso de uso aparte).
  - `infrastructure/django/`: `CustomerModel` (tabla `customers_customer`), mapper y `DjangoCustomerRepository`.
  - `api/`: serializers, vistas, paginación y urls (ver `ADR-clientes-mvp-contrato-api`).
- **Datos:** `id` UUID; `name` obligatorio, con trim, 1–150 caracteres; `phone` texto ≤ 30 (vacío = sin teléfono); `email` texto ≤ 254, vacío o con formato válido; `notes` texto ≤ 2000, puede ser vacío; `active` (default `True`); `created_at`, `updated_at`. El teléfono y el correo son opcionales; no se agregan los campos "futuros" de `ddd.md:252-259` (CRM fuera del MVP). **Sin unicidad** de nombre, teléfono ni correo: el duplicado es una advertencia, no una restricción de BD (REQ-CUS-006).
- **Normalización de teléfono (sin dependencia nueva):** función pura en el dominio, `normalize_phone(raw, default_country_code) -> str`, que sirve como `PhoneNumber` sin crear una clase de valor aparte (`ddd.md` sección 29: no abstraer sin necesidad). Reglas:
  1. Recorta y elimina espacios, guiones, puntos y paréntesis.
  2. Si empieza con `+` conserva el prefijo; si empieza con `00` lo reemplaza por `+`; si son solo dígitos, antepone `+` y el código de país por defecto (ver enmienda: si ya empiezan con el código de país seguido de 8 o más dígitos, solo se antepone `+`).
  3. Es **normalizable** si el resultado es `+` seguido de 8 a 15 dígitos (rango E.164 práctico); se guarda en esa forma (`+59176543210`).
  4. Si no es normalizable (letras, extensiones, longitud fuera de rango), **se guarda el texto recortado tal cual** y no se rechaza ("cuando sea posible").
  El **código de país por defecto** se inyecta desde la capa de aplicación leyendo el setting `DEFAULT_PHONE_COUNTRY_CODE` (variable de entorno con valor por defecto `591`, tomado del ejemplo de `ddd.md:271-273`). **Supuesto a confirmar con el negocio.** Un cliente existente cuyo teléfono se guardó sin normalizar solo coincide por texto exacto.
- **Comparación de duplicados:** igualdad exacta del campo `phone` ya normalizado (los no normalizables se comparan por su texto recortado). El repositorio expone `find_by_phone(phone, exclude_id=None)` y la búsqueda incluye clientes inactivos (se marcan como tales). Índice **no único** sobre `phone` para consultar rápido.
- **Búsqueda (REQ-CUS-003):** un solo parámetro; coincidencia parcial sin distinguir mayúsculas contra `name`, o, si el término contiene dígitos, contra `phone` usando solo los dígitos del término (`"765 432"` coincide con `+59176543210`). Implementada a mano con el ORM (sin `django-filter` ni búsqueda de texto completo).
- **Referencias históricas (REQ-CUS-002/005):** el `id` UUID nunca cambia y no hay operación de borrado (ni `DELETE` ni baja física en el repositorio); editar solo modifica atributos del cliente. Sales referenciará `customer_id` como UUID sin clave foránea entre apps (`ddd.md:890-902`). Anonimización queda fuera del MVP.
- **Estados** solo por `activate()`/`deactivate()`; los serializers validan forma y tipos, las reglas viven en el dominio.
- **Migración:** `customers/migrations/0001_initial.py` generada con `makemigrations`; solo crea la tabla e índice nuevos. Pruebas: dominio sin BD (`SimpleTestCase`, incluida la tabla de casos de normalización), casos de uso con repositorio en memoria y API con PostgreSQL.

## Alternativas consideradas
- **Librería `phonenumbers`:** normalización y validación rigurosas por país, pero es una dependencia nueva (`pip`) con datos de metadatos pesados para un MVP que solo necesita un formato canónico; además "cuando sea posible" tolera números no válidos. Descartada por ahora; se puede reemplazar `normalize_phone` por la librería sin cambiar el contrato.
- **Sin código de país por defecto (solo limpiar caracteres):** no inventa un supuesto de país, pero `76543210` y `+59176543210` no coincidirían como duplicados aunque sean el mismo cliente; menos útil para "duplicados evidentes". Descartada.
- **Dos columnas (`phone` crudo y `phone_normalized`):** conserva lo digitado, pero duplica datos y complica búsqueda y mapper; el dato crudo no es requerido. Descartada; si hiciera falta se agrega una migración aditiva.
- **Clase `PhoneNumber`/`EmailAddress` como Value Objects:** coincide con `ddd.md:263-281`, pero hoy solo habría funciones que devuelven `str`; se difiere hasta que el comportamiento crezca.
- **Restricción única sobre el teléfono:** garantiza la unicidad pero contradice REQ-CUS-006 (no bloquear) y rompe casos reales (familia que comparte teléfono).
- **Modelo Django sin entidad de dominio:** contradice `CLAUDE.md` y el patrón ya sentado por `catalog`.
- **Eliminación lógica con campo `deleted_at` además de `active`:** sin requisito que lo pida; `active` cubre REQ-CUS-005.

## Estrategia de rollback / mitigación
Cambio aditivo: tabla e índice nuevos, sin dependencias de otros módulos ni datos existentes. Rollback = revertir el PR y, si la migración ya se aplicó, `python manage.py migrate customers zero` (reversible, solo `CreateModel`/`AddIndex`). El nuevo setting tiene valor por defecto, así que no obliga a modificar `.env` ni rompe `production`. No toca autenticación.

## Consecuencias
- Queda fácil: Sales referencia clientes por UUID; cambiar la regla de normalización o adoptar `phonenumbers` es local a una función; probar todo sin BD.
- Queda más difícil: sin unicidad en BD, dos altas simultáneas con el mismo teléfono pueden coexistir (la detección es consultar-y-luego-insertar, advertencia y no garantía).
- Deuda aceptada: suposición de país por defecto (`591`); números sin normalizar solo coinciden por texto exacto; sin anonimización; búsqueda por `icontains` sin índice trigram (adecuada para el volumen de un MVP).

## Enmienda (2026-10-08, TASK-clientes-mvp, REV-2026-10-08-clientes-mvp-01)
Con aprobación explícita del usuario, la regla 2 de normalización se refina: un número de solo dígitos que **ya empieza con el código de país por defecto y deja 8 o más dígitos después** se toma como ya prefijado (solo se antepone `+`), p. ej. `591 76543210` → `+59176543210` (antes se obtenía `+59159176543210`, un número corrupto que además no se detectaba como duplicado de `76543210`). Un número local de 8 dígitos que empieza con `591` sigue siendo local. Límite aceptado: con códigos de país distintos y números locales largos la heurística podría tomar por prefijado un local; el valor del país es configurable. No cambia el resto de la decisión; se recomienda que `delivery-architect` la formalice si prefiere un ADR nuevo.
