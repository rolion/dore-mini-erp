# DDR-registro-usuarios-empresa-multitenant-pantalla-registro: Pantalla de registro con empresa y señales de empresa en la sesión

**Estado:** Propuesto
**Task relacionado:** TASK-registro-usuarios-empresa-multitenant
**Fecha:** 2026-10-12

## Contexto
El requerimiento pide registrar usuarios reutilizando el formulario sign-up de la plantilla, con **nombre de empresa obligatorio**; todo usuario ve solo los datos de su empresa y existe un perfil admin con acceso total a su empresa.

Hechos de la investigación y de la revisión del código para esta etapa:
- `frontend/panel_admin/src/app/authentication/signup/signup.component.ts` es un formulario de la plantilla **sin conexión**: `onSubmit()` valida y termina (`// register user call here..`), usa `UntypedFormBuilder`, textos en inglés y botón `disabled` mientras el formulario sea inválido.
- `signup.component.html` conserva la **imagen lateral** (`register-card-img`, `register.jpg`) en un `.register-container` de 2 columnas, el checkbox "I Accept Terms And Condition" (enlace a `javascript:void(0)`: no existe ningún documento de términos) y el bloque "Or Signup With" con iconos sociales **no funcionales**. Desde `TASK-pocketbiz-branding-logos` ya comparte logo (`main-logo.png`) con el login.
- `signin.component.html` ya fue rediseñado: tarjeta única centrada (`.login-card--single`, `_auth.scss`), sin imagen lateral, `NonNullableFormBuilder`, botón que solo se deshabilita mientras `loading`, errores en un `alert alert-danger` y etiquetas "Usuario"/"Contraseña" en español. El login se hace con **`username`** (`core/service/auth.service.ts:29-31`).
- El patrón de formularios ya construidos de la app (p. ej. `features/customers/pages/customer-form`) muestra errores de campo con `form-text text-danger` y un `serverErrors` por campo que se limpia al editar.
- El header (`layout/header/header.component.html`, menú de usuario) muestra datos fijos de la plantilla: `Hello Sarah..` y `assets/images/user.png`; hoy la sesión no expone empresa ni nombre real.
- La plantilla documenta las páginas de autenticación como parte de `authentication/` (`panel_admin_doc/folder-structure.html:242,272`) y la validación de formularios en `panel_admin_doc/form-validation.html`; no existe una pantalla de "gestión de usuarios" en la plantilla que sea aplicable a este requerimiento.

Preguntas de la investigación que **este DDR no resuelve** (son de `delivery-architect`): si registrarse crea o se une a una empresa, si el login sigue por `username` o pasa a correo, y qué devuelve el backend tras el alta. El diseño abajo queda condicionado explícitamente a esas respuestas donde se indica.

## Pantallas/flujos afectados
1. **Registro** (`/authentication/signup`): una persona nueva ingresa sus datos y el nombre de su empresa y crea la cuenta.
2. **Post-registro**: qué ve la persona al terminar con éxito.
3. **Menú de usuario del header** (todas las pantallas autenticadas): la persona ve con qué usuario y en qué empresa está operando.
4. **Login** (`/authentication/signin`): sin cambios de diseño; solo el enlace "Sign Up" ya apunta al registro.

No se diseña una pantalla de gestión de usuarios/roles: el requerimiento no la pide (el admin "tiene acceso a todo" y no se pidió alta de usuarios adicionales ni asignación de roles desde la UI).

## Componentes/patrones elegidos

### 1. Registro — reutiliza `SignupComponent`
- **Contenedor:** se alinea con el login: tarjeta única centrada con las clases de plantilla ya existentes (`.login-card.login-card--single` + `.login-body` + `.brand-wrapper`, `src/assets/scss/components/_auth.scss`), **sin imagen lateral**. Mismo logo `main-logo.png` ya presente. Razón: con un campo más y confirmación de contraseña, el formulario crece y una tarjeta angosta de una columna es más legible; además queda visualmente idéntica al login.
- **Campos, en este orden** (una columna, salvo nombre/apellido en dos columnas como en la plantilla):
  | Campo | Control | Reglas visibles |
  |---|---|---|
  | **Nombre de la empresa** * | texto, icono `briefcase` (`i-feather`, como los demás `login-icons`) | obligatorio; recortar espacios; mismo largo máximo que el backend defina |
  | Nombre * / Apellido * | texto, 2 columnas (`col-md-6`) | obligatorios |
  | Usuario * | texto, icono `user` | obligatorio; es lo que se usa en el login hoy (ver "Pendiente de arquitectura") |
  | Correo * | `type="email"` | formato de correo |
  | Contraseña * | `type="password"` | obligatoria; texto de ayuda con la regla vigente del backend |
  | Confirmar contraseña * | `type="password"` | debe coincidir (validación solo de cliente) |
- **Reglas de formulario:** Reactive Forms **tipados** (`NonNullableFormBuilder`, como `signin.component.ts`), no `UntypedFormBuilder`; la lógica de la llamada a la API va en `AuthService` (servicio inyectable), no en el componente.
- **Botón:** "Crear cuenta", habilitado salvo durante el envío (`loading`), igual que el login: al enviar con datos inválidos se marcan los campos y se muestra el motivo. Se elimina el patrón actual `[disabled]="registerForm.invalid"` porque un botón apagado no explica qué falta.
- **Validación visible:** por campo con `form-text text-danger` bajo el control (patrón de `customer-form`), con un `serverErrors` por campo que se limpia al editar; un `alert alert-danger` arriba del botón para errores generales (red, 429/throttle, 5xx), como el login.
- **Se elimina:** (a) el bloque "Or Signup With" (iconos sociales sin función; no hay proveedores de identidad) y (b) el checkbox de "Terms And Condition" (apunta a nada; si el negocio necesita términos legales se añade con un documento real). Se mantiene el pie "¿Ya tienes cuenta? Inicia sesión" con `routerLink="/authentication/signin"`.
- **Idioma:** textos en español, igual que las pantallas de negocio y las etiquetas "Usuario"/"Contraseña" del login. No se introduce `ngx-translate` para esta pantalla (el login tampoco lo usa).

### 2. Post-registro
- **Flujo elegido:** registro exitoso → la persona **entra directo** a `DEFAULT_ROUTE_AFTER_LOGIN` (`/dashboard/main`, ya definido en `signin.component.ts`), con la sesión ya iniciada. Sin pantalla intermedia ni verificación de correo (no existe infraestructura de correo en el proyecto).
- **Condición:** requiere que el registro devuelva token y usuario igual que el login (decisión de arquitectura). Si arquitectura decide que el registro no inicia sesión, el flujo es: redirigir a `/authentication/signin` con un `alert-success` "Cuenta creada. Inicia sesión." (estado pasado por `router.navigate(..., { state })`).

### 3. Menú de usuario del header
- Reemplazar el saludo fijo `Hello Sarah..` del `dropdown-title` (`header.component.html`, menú de usuario) por el **nombre y apellido** de la sesión (con `username` como respaldo) y, justo debajo, una línea de texto atenuado con el **nombre de la empresa**. Se reutiliza el dropdown existente (`ngbDropdownMenu .dropdown-title`), sin componentes nuevos.
- Motivo: con aislamiento por empresa, la persona debe poder confirmar en qué empresa opera; hoy el header muestra datos de demostración.
- Requiere que `User` (`core/models/user.ts`) y la respuesta de login/registro incluyan nombre de empresa (decisión de arquitectura).
- La imagen `user.png` y las entradas Profile/Email/Settings de la plantilla **no se tocan** (fuera de alcance).

## Alternativas consideradas
- **Mantener el layout de 2 columnas con imagen (`register-card`)** frente a **tarjeta única como el login** (elegida). La primera respeta la decisión previa de branding ("mantener imagen lateral porque no se pidió quitarla") y su costo es nulo, pero deja registro y login con aspectos distintos y un formulario alto en media columna. **Supuesto a confirmar por la persona**: se prefiere coherencia con el login; si prefiere conservar la imagen, el resto del DDR no cambia, solo el contenedor.
- **Campo de empresa al final del formulario** frente a **primero** (elegido): la empresa define el espacio de trabajo y es el dato que la persona no encuentra en el formulario genérico de la plantilla; ponerlo primero evita que pase desapercibido.
- **Sin confirmación de contraseña** (como la plantilla) frente a **con confirmación** (elegida): hoy no hay recuperación de contraseña operativa (`forgot`/`reset` son demos de la plantilla), así que un error de tipeo bloquea la cuenta; el costo es un campo más.
- **Botón deshabilitado hasta que el formulario sea válido** (plantilla) frente a **habilitado y validar al enviar** (elegida, igual que el login): evita el "botón apagado sin explicación".
- **Mostrar solo el nombre de empresa en el header** frente a **usuario + empresa** (elegida): solo la empresa pierde la referencia de con qué usuario se opera; el costo extra es una línea.
- **Pantalla de selección/gestión de empresas o de usuarios** para el admin: descartada por ahora; no se pidió, y depende de preguntas abiertas de arquitectura (usuarios por empresa, roles).
- **Registro en dos pasos (cuenta, luego empresa)**: añade pantallas y estados parciales sin beneficio para un formulario de seis campos. Descartado.

## Comportamiento por privilegio/estado
- **Sin sesión** (anónimo): ve login y registro. Con sesión iniciada que visita `/authentication/signup`, hoy la plantilla no la redirige; se deja igual (fuera de alcance), anotado como deuda.
- **Rol admin (único hoy):** ve toda la aplicación de su empresa; no hay variantes visuales por rol. **No se agrega lógica de ocultar/deshabilitar por rol** hasta que exista un segundo rol (YAGNI).
- **Estados de la pantalla de registro:** inicial · enviando (botón deshabilitado, `loading`) · error de campo (por `serverErrors`, p. ej. empresa/usuario ya existente, contraseña débil) · error general (alerta superior) · éxito (navegación).
- **Nota de seguridad:** todo lo anterior es UX. **Requiere que arquitectura defina cómo el servidor aísla los datos por empresa y verifica el rol admin** (a partir del token/sesión, no de lo que el cliente envíe); el frontend no debe ser la única barrera ni decidir a qué empresa se accede. El nombre de la empresa que se muestra en el header es solo informativo.

## Pendiente de arquitectura (condiciona este diseño)
1. ¿El registro **crea** una empresa o **se une** a una? Define los mensajes de error/éxito del campo "Nombre de la empresa" (p. ej. "Ya existe una empresa con ese nombre").
2. ¿Identidad por `username` o por correo? Si es correo, se elimina el campo "Usuario" y el login pasa a "Correo".
3. ¿El registro devuelve sesión (token + usuario con empresa)? Define el post-registro (entrada directa o redirección al login).
4. Contrato de errores por campo del registro (formato de `400`), para mapearlo a `serverErrors`.

## Consecuencias
- Registro y login quedan visualmente consistentes y con el mismo patrón de formulario tipado, validación y errores.
- Se elimina de la pantalla de registro código muerto de la plantilla (social, términos, imagen lateral).
- **Deuda visual aceptada:** el login conserva el bloque "Or Login With" con iconos sociales sin función y textos en inglés mezclados ("Remember me", "Sign in", "Forgot password ?"); el registro nuevo quedará en español y sin social, por lo que **ambas pantallas diferirán en esos detalles** hasta limpiar el login (puede ir en una tarea aparte, o añadirse al plan si la persona lo pide).
- El `register.jpg` y las reglas `.register-card*` de `_auth.scss` quedan sin uso tras el cambio; limpiarlos es opcional.
- Si más adelante el admin necesita crear usuarios/asignar roles, será una pantalla nueva con su propio DDR; este diseño no la anticipa.
- Verificación: es visual y de formulario; el plan debe cubrir el spec de `SignupComponent` (hoy solo "should create"), `AuthService.register` y el campo requerido.
