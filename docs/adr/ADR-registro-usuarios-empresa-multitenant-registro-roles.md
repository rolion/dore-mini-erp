# ADR-registro-usuarios-empresa-multitenant-registro-roles: Registro público que crea la empresa, rol admin y permiso por defecto

**Estado:** Propuesto
**Task relacionado:** TASK-registro-usuarios-empresa-multitenant
**Fecha:** 2026-10-12

## Contexto
No existe registro de usuarios: solo `POST /api/auth/login/` y `/logout/` (`modules/accounts/api/urls.py:5-8`); los usuarios se crean con `createsuperuser`. `User(AbstractUser)` está vacío (`accounts/models.py:4-6`) y no hay uso de grupos ni permisos. El DDR `DDR-registro-usuarios-empresa-multitenant-pantalla-registro` define el formulario (empresa, nombre, apellido, usuario, correo, contraseña) y la entrada directa al dashboard tras registrarse.

Decisiones de negocio ya tomadas (usuario, esta etapa): el registro público **solo crea empresas nuevas**; un nombre de empresa existente se rechaza; los usuarios adicionales de una empresa los agrega su admin (por ahora vía Django admin; sin pantalla en esta tarea). Cada usuario es admin de su empresa por el momento; el admin accede a todo lo de su empresa.

Decisiones previas que se conservan: token DRF, login por `username`, `accounts` como infraestructura de identidad sin `domain/application` (`ADR-frontend-login-backend-autenticacion-token`, `ADR-inicializar-backend-django-modelo-usuario`), throttling por scope en el login (`accounts/api/views.py:18-19`, `config/settings/base.py:91-93`).

## Decisión
1. **`Company` en `accounts`:** entidad con `id` (UUID), `name`, `is_active`, `created_at`. El nombre es **único sin distinguir mayúsculas ni espacios sobrantes** (restricción de BD sobre `Lower(name)` más normalización de espacios antes de guardar, mismo patrón que `expenses_category_name_ci_unique`). Las empresas **no se borran** (se desactivan).
2. **`User.company`:** FK a `Company` (`on_delete=PROTECT`), **nullable** para permitir superusuarios de operación creados con `createsuperuser` que no pertenecen a ninguna empresa. Un usuario sin empresa no accede a la API de negocio (ver ADR de propagación). Un usuario inactivo o de una empresa inactiva no puede iniciar sesión (mismo 401 genérico).
3. **Rol:** campo `User.role` (`CharField` con `TextChoices`), hoy solo `admin` (default `admin`). Se elige un campo simple en lugar de `Group`/permisos de Django porque hoy hay un único perfil con acceso total; evita tablas y semillas de permisos sin uso. Cuando aparezca un segundo rol se añade el valor y el **default pasa al menos privilegiado** en esa misma migración.
4. **Permiso por defecto de la API:** una clase DRF `CompanyAdminPermission` en `accounts/api/permissions.py` (autenticado **y** `company` activa **y** `role == admin`) pasa a ser `DEFAULT_PERMISSION_CLASSES` en `config/settings/base.py`. Se referencia por ruta de texto desde settings, de modo que los módulos de negocio no importan `accounts`. Los endpoints públicos conservan `AllowAny` explícito (login, registro, health); `logout` conserva `IsAuthenticated`. Deniega por defecto: un view nuevo queda protegido sin acción del autor.
5. **Registro:** `POST /api/auth/register/`, público (`authentication_classes = []`, `AllowAny`, como el login).
   - Entrada: `company_name`, `username`, `first_name`, `last_name`, `email`, `password`. La confirmación de contraseña es solo de cliente.
   - Efecto (una sola transacción): crea `Company`, crea `User` (rol `admin`, `company` asignada, contraseña validada con `AUTH_PASSWORD_VALIDATORS`) y crea su token.
   - Salida: `201` con la **misma forma que login**: `{ token, user: { id, username, first_name, last_name, role, company: { id, name } } }`, para que el frontend entre directo al dashboard (según DDR).
   - Errores `400` con dict por campo (`company_name`, `username`, `password`, …) mapeable a los `serverErrors` del formulario. Nombre de empresa o usuario ya existentes → `400` sobre ese campo. Una carrera entre dos altas iguales se resuelve con la restricción de BD (captura `IntegrityError`, igual que `DjangoExpenseCategoryRepository.save`).
   - **Throttling:** scope `register` (tasa inicial `5/hour` por IP, configurable en `DEFAULT_THROTTLE_RATES`).
   - **Interruptor:** variable de entorno `REGISTRATION_ENABLED` (default `True`; `production` la lee y puede ponerla en `False`); si es falso el endpoint responde `404`/`403` sin crear nada. Es la mitigación operativa ante abuso.
6. **Login y respuesta de usuario:** `UserSerializer` agrega `role` y `company {id, name}` de forma **aditiva** (contrato de login compatible); el frontend los guarda en la sesión (`User` de `core/models/user.ts`) para mostrar usuario y empresa en el header (DDR). No se añade endpoint `me`.
7. **Alta de usuarios adicionales:** por ahora solo vía Django admin (`accounts/admin.py` con `Company` y `User` incluyendo `company` y `role`), operado por quien administra la plataforma. Un admin de empresa **no** crea usuarios desde la API/UI en esta tarea (fuera de alcance; requiere su propio DDR/ADR).
8. **Lógica de registro:** una función de aplicación simple en `accounts` (`accounts/registration.py`) invocada por el view, con el serializer validando forma y tipos. Sin capas `domain/application` (consistente con ADR previos; no hay reglas de negocio que lo justifiquen).

## Alternativas consideradas
- **Unirse automáticamente a la empresa existente por nombre:** simple, pero cualquiera que conozca el nombre accede a todos sus datos. Descartada por el usuario.
- **Unirse con aprobación del admin:** correcta funcionalmente, pero requiere flujo y pantalla de aprobación, usuarios en estado pendiente y notificación; fuera del alcance acordado.
- **`Group`/`Permission` de Django:** extensible, pero implica semillas, migraciones de datos y verificación de pertenencia en cada request para un único rol. Se aplaza hasta que haya más de un rol real.
- **Usar `is_staff`/`is_superuser` como "admin":** mezcla acceso al Django admin (operación de plataforma) con el rol de empresa; un admin de empresa no debe entrar al admin de Django.
- **Login por correo:** exige cambiar `USERNAME_FIELD`, el login y datos existentes; no pedido. Se conserva `username` (el campo "Usuario" del formulario del DDR); `email` se guarda sin exigir unicidad.
- **Empresa identificada por `slug`/subdominio:** no hay despliegue multi-dominio ni requisito de URL por empresa.
- **Registro en dos pasos (crear usuario, luego crear empresa):** deja usuarios sin empresa y estados parciales.

## Estrategia de rollback / mitigación
- **Aditivo:** nuevo modelo/campos y un endpoint; no altera los existentes. Rollback: revertir el PR y `migrate accounts 0001` (elimina `Company` y las columnas nuevas; las asignaciones se pierden, no los usuarios).
- **Cambio de `DEFAULT_PERMISSION_CLASSES`:** es el punto sensible. Mitigación: la migración de datos asigna a **todos** los usuarios existentes la empresa por defecto con rol `admin`, de modo que nadie pierde acceso al desplegar; las pruebas del módulo verifican que un usuario sin empresa recibe 403 y uno con empresa accede.
- **Abuso del registro público:** throttle por IP + interruptor `REGISTRATION_ENABLED`. Residual: enumeración de nombres de empresa y de usuarios mediante los errores `400` (inherente a un registro con nombre único; aceptado, limitado por throttling).
- **Contraseñas:** se guardan con el hasher de Django; la respuesta nunca incluye contraseña ni hash (misma prueba que el login).

## Consecuencias
- Fácil: reutiliza token y forma de respuesta del login; el frontend entra directo; el permiso por defecto protege views futuros.
- Difícil: sin pantalla/endpoint para que un admin de empresa agregue usuarios, el crecimiento de una empresa depende de quien opere Django admin (limitación aceptada por decisión de negocio, a resolver en otra tarea).
- Deuda aceptada: un solo rol; tokens sin expiración; un usuario pertenece a una sola empresa; `accounts` sigue fuera de la lista de módulos de `ddd.md` (el plan debe documentarlo junto con el modelo `Company`).
- Nuevas variables de entorno: `REGISTRATION_ENABLED` (opcional, default `True`); el plan debe actualizar `.env.example` y `CLAUDE.md`.
