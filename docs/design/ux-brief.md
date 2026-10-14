# UX Brief — Landing page de PocketBiz

**Estado:** Propuesto (pendiente de confirmación del usuario)
**Fecha:** 2026-10-12
**Etapa:** `delivery-ux-research` · siguiente: `delivery-design-system` / `delivery-ui-design`
**Alcance:** definición de contenido y estructura de la landing pública. No incluye pantallas en Stitch ni código.

Convención de etiquetas: **[Confirmado]** respaldado por documentos o código del repo · **[Hipótesis]** inferencia sin investigación de usuarios · **[Decisión propuesta]** a validar.

---

## 1. Contexto y evidencia

### 1.1 Qué es PocketBiz hoy (fuente: repo, no marketing)
Aplicación web (Angular + Django/DRF) para pequeños negocios que venden por canales informales. El eslogan "Tu negocio en el bolsillo" es de marca (`DDR-pocketbiz-branding-logos-marca-y-color.md`; el logo trae "tu negocio en el bolsillo" en minúsculas). El ejemplo de negocio en `docs/architecture/ddd.md` es una venta de packs de cuñapés en Bolivia (Bs, prefijo +591).

### 1.2 Funcionalidades que existen [Confirmado]
Fuentes: `TASK-catalogo-productos-mvp`, `TASK-clientes-mvp`, `TASK-ciclo-pedido-entrega-cobro`, `TASK-gastos-reporting-mvp`, `TASK-registro-usuarios-empresa-multitenant`, rutas en `app.routes.ts`.

| Área | Qué puede hacer la persona (hoy) | Fuente |
|---|---|---|
| Registro | Crear cuenta desde `/authentication/signup` con nombre de empresa; entra directo al panel. Cada registro crea una empresa nueva (nombre repetido se rechaza). | TASK registro, DDR registro |
| Aislamiento | Cada usuario ve solo los datos de su empresa (filtrado en servidor). | ADR modelo-aislamiento |
| Productos | Crear/editar con nombre, descripción y precio; activar/desactivar; buscar. Los pedidos viejos conservan nombre y precio. | TASK catálogo |
| Clientes | Crear con solo el nombre (teléfono, correo y notas opcionales); buscar por nombre/teléfono; aviso de teléfono duplicado; historial de compras; desactivar. Crear cliente al vuelo desde un pedido. | TASK clientes |
| Pedidos | Ítems con cantidad, descuento, canal (WhatsApp, Facebook, Instagram, venta directa, feria, otro), fecha de entrega prevista, notas. Estados: nuevo → en preparación → listo → entregado; cancelar con motivo. | TASK ciclo-pedido |
| Cobros | Pagos parciales; métodos efectivo, QR, transferencia, tarjeta, otro; saldo pendiente. **Entrega y pago son independientes** ("entregado con saldo", "pagado, pendiente de entrega"). | TASK ciclo-pedido |
| Gastos | Categorías propias, gasto con monto/fecha/categoría/método de pago/proveedor/notas; anulación lógica; filtros por fecha y categoría. | TASK gastos |
| Reportes | Periodo día/semana/mes/rango. Ventas, gastos, **ganancia estimada**, pedidos, ticket promedio, ventas por canal, productos más vendidos, clientes con mayor compra, gastos por categoría, pendientes de entrega y de cobro. | DDR dashboard, ADR contrato reportes |

Criterio de ventas del reporte [Confirmado]: pedidos no cancelados, por fecha de pedido; **no** es lo cobrado ni incluye costo de producción. "Ganancia estimada = ventas − gastos registrados"; la etiqueta es obligatoria y no debe sugerir utilidad contable (`ddd.md`, REQ-REP-005).

### 1.3 Lo que NO existe y la landing no puede prometer [Confirmado]
- Facturación electrónica, contabilidad, inventario/stock, producción/costos de receta (`ddd.md` §24–25, fuera del MVP).
- WhatsApp automático / integración con redes; IA (`ddd.md` §24).
- Equipo de varios usuarios autogestionado: solo existe el rol `admin`; los usuarios adicionales los da de alta un admin vía Django admin, sin pantalla (TASK registro).
- Recuperación de contraseña: las páginas `forgot`/`reset` son demos de la plantilla, sin backend (DDR registro; grep sin resultados en `backend/modules`).
- Exportar a Excel/PDF, comparación entre periodos, tendencias (DDR dashboard).
- Corregir o anular pagos registrados (riesgo operativo anotado en TASK ciclo-pedido).
- App móvil nativa, modo sin conexión o instalable: no hay manifest ni service worker (DDR branding: "no existe manifest").
- **Planes y límites:** el usuario definió un modelo comercial (ver §1.6), pero **el producto no lo implementa**: no hay plan, suscripción, cobro ni límite de productos/ventas/gastos en backend ni frontend. Cualquier texto de planes en la landing describe una oferta que hoy no se aplica.
- Términos y condiciones, política de privacidad: no hay ningún documento (DDR registro eliminó el checkbox de términos "porque apunta a nada").
- Testimonios, cifras de clientes o resultados: no existen y no se inventan.

### 1.4 Referencias de Stitch
Actualizado 2026-10-12: la conexión al MCP `stitch` funciona (la variable `STITCH_API_KEY` no llegaba al proceso hasta reiniciar el equipo). `list_projects` (`owned` y `shared`) devuelve vacío: **no existe proyecto Stitch de PocketBiz** y tampoco `docs/design/screens.md`. Habrá que crearlo en `delivery-ui-design` y registrar su ID. No se usó Stitch en esta etapa.

### 1.6 Decisiones del usuario (2026-10-12)
- **Modelo comercial [Confirmado por el usuario]:**

| | Gratis | Pro |
|---|---|---|
| Precio | Bs 0 | **Bs 30 por mes** o **Bs 350 por año** (Q11) |
| Productos | 1 | Sin restricciones |
| Clientes | 1 (Q19) | Sin restricciones |
| Ventas | 2 | Sin restricciones |
| Gastos | 2 | Sin restricciones |
| Dashboard y reportes de ventas y gastos | Sí (Q19) | Sí |

  - **Nombre del plan:** el usuario pasó de "Base" a "**Pro**" en su última respuesta; se adopta "Pro" y se confirma en Q22.
  - "Transacción" = el registro de **una venta** o de **un gasto** (Q15).
  - Los límites aplican **solo al plan gratuito** (Q17). Con el límite alcanzado no se pueden ingresar más datos hasta el día siguiente o hasta pasar a Pro (Q14); **la persona sigue viendo sus datos** (Q17). Pro no tiene restricciones.
  - Cálculo (mío, verificable): 12 × Bs 30 = Bs 360; el plan anual (Bs 350) ahorra Bs 10 (≈2,8 %). No presentarlo como "descuento grande".
  - **Pago (Q16/Q18):** no hay pasarela y, **de momento, ninguna acción de compra**; el flujo de pago es un tema pendiente. La landing muestra el plan Pro como información, sin botón que simule una compra.
  - **Vencimiento (Q20):** al vencer el plan, la cuenta **se bloquea hasta que se realice el pago**. Esto contradice la ausencia de forma de pagar: ver Q21.
- **Q2, móvil [Confirmado por el usuario]:** las pantallas de negocio funcionan en celular. **Evidencia añadida el 2026-10-13:** captura real del dashboard a ≈396 px (`docs/design/exports/landing/referencias-producto/dashboard-movil-396.png`). Se acepta como base para el mensaje "en el bolsillo", sin decir "app".
- **Canal de venta [Evidencia visual, 2026-10-13]:** el formulario "Nuevo pedido" tiene un selector obligatorio "Canal de venta" (captura `nuevo-pedido-canal-de-venta.png`); la landing puede afirmarlo.
- **Estados visibles [Evidencia visual]:** el detalle del pedido muestra Entrega ("Listo", "Entregado") y Cobro ("Pendiente", "Pagado", "Sin saldo") por separado, con "Saldo Bs 28.00".
- **Formato monetario real:** `Bs 28.00` (punto decimal). La landing debe usarlo.

### 1.5 Estado del producto a considerar
El producto está "en construcción" (`CLAUDE.md`). Los TASK de varias features figuran como "listo para aprobación humana"; verificar qué está en `main` y desplegado antes de publicar la landing. Los textos solo deben describir lo que esté realmente disponible a la fecha de publicación.

---

## 2. Público objetivo

> Todo este apartado es **[Hipótesis]** derivada de documentos del repo; no hay entrevistas ni datos de usuarios. Validar con 3–5 conversaciones con dueños/as de negocios antes de dar por cerrada la propuesta de valor.

**Persona principal:** dueño/a o administrador/a de un emprendimiento pequeño que vende productos físicos por **WhatsApp, Facebook, Instagram, en feria o directo**, que lo opera solo/a o con muy poca gente, y que hoy probablemente lleva el control en chats, cuaderno, hojas de cálculo o de memoria.

**Tarea principal (jobs-to-be-done):** saber con certeza *qué vendí, quién me debe, qué tengo que entregar y en qué gasté*, sin aprender un sistema contable.

**Problemas que PocketBiz resuelve (respaldados por funciones reales):**
1. Pedidos y cobros dispersos en conversaciones → un solo lugar con estado de entrega y de pago por pedido.
2. No saber cuánto le deben ni a quién → saldo pendiente y lista "por cobrar".
3. Gastos sin registrar → no ve cuánto le queda → gastos por categoría y ganancia estimada.
4. No saber qué canal o producto rinde → ventas por canal, productos y clientes más vendidos.

**No es para (por ahora):** negocios que necesitan inventario/stock, facturación electrónica, contabilidad formal, o varios usuarios con permisos diferenciados.

**Contexto de uso [Hipótesis]:** mayormente celular y a ratos libres. La promesa "en el bolsillo" **solo se puede sostener si la web funciona bien en móvil** (ver pregunta Q2).

---

## 3. Propuesta de valor

**Frase propuesta [Decisión propuesta]:**
> Registra tus pedidos, cobros y gastos en un solo lugar y mira, de un vistazo, cuánto vendiste, qué te deben y qué tienes que entregar.

**Apoyos (cada uno con respaldo real):**
- Pedidos, cobros y gastos juntos, sin contabilidad compleja.
- Separa **entrega** y **pago**: sabes qué está entregado y sigue sin cobrarse, y qué está pagado y falta entregar.
- Resumen por día, semana o mes con una **ganancia estimada** (ventas − gastos registrados), explicada sin tecnicismos.
- Hecho para vender por WhatsApp, redes, feria o directo.
- Los datos son de tu empresa y solo los ven los usuarios de tu empresa.

**Cómo se usa el eslogan:** "Tu negocio en el bolsillo" como titular de marca en el hero; el subtítulo concreta *qué* controla. No usarlo como prueba de que existe app móvil.

**Tono [Decisión propuesta]:** español, cercano y directo (tú), sin jerga contable ("devengado", "utilidad"); moneda en Bs en los ejemplos.

---

## 4. Objetivo de la landing y CTA

**Objetivo principal:** que la persona **cree su cuenta** (registro, que crea su empresa y la lleva directo al panel).

| | Texto propuesto | Destino |
|---|---|---|
| CTA primario | **Empezar gratis** | `/authentication/signup` |
| CTA secundario | Iniciar sesión | `/authentication/signin` |
| Con sesión activa | Ir a mi panel | `/dashboard/main` |

Reglas:
- "Gratis" se permite **solo** si el límite del plan gratuito (1 producto, 2 ventas, 2 gastos) se muestra en la propia página, cerca del CTA o en la sección de planes. No usar "sin tarjeta" ni "prueba gratis" (no confirmado).
- Un solo registro sirve a ambos planes (se empieza en gratis). La tarjeta Pro **no lleva botón de compra** por ahora (Q18); no usar "Pagar", "Comprar" ni "Contratar" hasta que exista un flujo definido (Q21).
- Repetir el CTA primario en header, hero y cierre. Un solo objetivo; no competir con enlaces secundarios.
- Si `REGISTRATION_ENABLED = False` (interruptor existente en backend), la landing no debe ofrecer registro abierto: ver estados en §6.
- Métrica propuesta (a instrumentar en otra etapa, no hay analítica hoy): clics en CTA primario y registros completados. No se fijan metas numéricas.

---

## 5. Arquitectura de información: secciones y mensaje

Una sola página con scroll; navegación superior con anclas.

| # | Sección | Mensaje principal | Contenido / evidencia | Acción |
|---|---|---|---|---|
| 0 | **Cabecera** (fija) | PocketBiz: entrar o crear cuenta. | Logo `main-logo`; anclas Qué puedes controlar · Cómo funciona · Preguntas; Iniciar sesión; Crear mi cuenta. | CTA primario / secundario |
| 1 | **Hero** | **Tu negocio en el bolsillo.** Pedidos, cobros y gastos en un solo lugar. | Eslogan, subtítulo con la propuesta de valor, CTA, imagen del producto real (captura del dashboard/pedido; ver Q5). | Crear mi cuenta |
| 2 | **El problema** *(hipótesis)* | "¿Tus ventas viven en chats, cuadernos y de memoria?" Eso se traduce en cobros olvidados y gastos sin ver. | 3 frases cortas de reconocimiento. Sin cifras ni estudios. Validar con entrevistas; si no se valida, reducir a una línea o eliminar. | — |
| 3 | **Qué puedes controlar** | Cuatro cosas, en un solo lugar. | Tarjetas: **Pedidos y entregas** (estados, canal) · **Cobros** (pagos parciales, saldo) · **Gastos** (categorías, método de pago) · **Clientes y productos** (historial, precio, activo/inactivo). | — |
| 4 | **Entrega y pago, por separado** | Sabes qué entregaste y qué te falta cobrar. | Ejemplo visual con los dos estados independientes (captura real o ilustración con datos ficticios marcados "ejemplo"). Es el diferenciador más concreto del producto. | — |
| 5 | **Tu resumen** | Mira cuánto vendiste, cuánto gastaste y cuánto te queda, **estimado**. | Periodo día/semana/mes/rango; ventas, gastos, **ganancia estimada** con nota "ventas − gastos registrados; no es utilidad contable"; pendientes de entrega y cobro; por canal y productos más vendidos. | — |
| 6 | **Cómo empezar** | En tres pasos. | 1) Crea tu cuenta con el nombre de tu empresa. 2) Registra tus productos, clientes y primer pedido. 3) Mira tu resumen. Los pasos coinciden con el flujo real (registro → panel). | Crear mi cuenta |
| 6b | **Planes** | Empieza gratis; pasa al plan base cuando lo necesites. | Dos tarjetas. **Gratis:** 1 producto, 1 cliente, 2 ventas y 2 gastos, con dashboard y reportes de ventas y gastos; al llegar al límite sigues viendo tus datos y registras de nuevo al día siguiente. **Pro:** Bs 30 al mes o Bs 350 al año, sin restricciones. Selector mensual/anual. CTA "Empezar gratis" en Gratis; la tarjeta Pro **no lleva botón de compra** mientras no exista flujo de pago (Q18, Q21). No atribuir a Pro beneficios no confirmados (usuarios, soporte, exportación). | Empezar gratis |
| 7 | **Tus datos, tu empresa** | Cada empresa ve solo sus datos. | Aislamiento por empresa (ADR). Sin prometer certificaciones, cifrado específico ni cumplimiento legal que no se verificó. | — |
| 8 | **Preguntas frecuentes** | Respuestas honestas sobre alcance y límites. | Ver §7. Incluye lo que PocketBiz **no** hace. | — |
| 9 | **Cierre** | Empieza a ver tu negocio con claridad. | Repetición de eslogan, CTA primario y enlace a iniciar sesión. | Crear mi cuenta |
| 10 | **Pie** | — | Logo, enlace a iniciar sesión, contacto (Q6), enlaces legales (Q4) **solo si existen**. Sin redes ni teléfonos inventados. | — |

**Orden:** reconocimiento (1–2) → qué hace (3–5) → fricción baja (6) → confianza (7–8) → cierre (9). Las secciones 2 y 7 pueden fusionarse con vecinas si el contenido queda delgado.

---

## 6. Especificación de la pantalla

**Pantalla única: Landing** (ruta pública; ubicación pendiente, Q7).

- **Propósito:** explicar qué es PocketBiz y llevar a crear cuenta.
- **Datos:** contenido estático; sin llamadas a la API. (Opcional futuro: consultar si el registro está habilitado.)
- **Acción principal:** Crear mi cuenta → `/authentication/signup`.
- **Acciones secundarias:** Iniciar sesión; anclas de navegación; abrir FAQ.
- **Viewports de referencia:** 1440 y 390 px. Temas: light (dark solo si el producto lo expone en páginas públicas; no requerido).
- **Marca:** `main-logo.png` / `simple-logo.png`, primario `#1677FF`, Inter (DDR branding); sin introducir otra paleta.

**Estados**

| Estado | Comportamiento |
|---|---|
| Visitante anónimo | Página completa con CTA "Crear mi cuenta". |
| Con sesión activa | Cabecera y CTA cambian a "Ir a mi panel"; sin forzar redirección. |
| Registro deshabilitado (`REGISTRATION_ENABLED=False`) | Sin CTA de registro abierto; mensaje "El registro no está disponible por ahora" y acceso a iniciar sesión. Requiere que el frontend conozca el estado (decisión de arquitectura; hoy el backend solo responde 403 al registrar). |
| Carga / error | Contenido estático: no hay spinner ni error de datos. Imágenes con `alt` y dimensiones reservadas. |
| Móvil | Navegación colapsada con CTA siempre visible; una columna; sin scroll horizontal. |

**Criterios de aceptación verificables**
- AC-01: El hero muestra "Tu negocio en el bolsillo" y un CTA "Crear mi cuenta" visible sin hacer scroll en 1440×900 y 390×844.
- AC-02: Todo CTA primario navega a `/authentication/signup`; todo CTA secundario a `/authentication/signin`.
- AC-03: Cada afirmación de funcionalidad de la página corresponde a una fila de §1.2; ninguna corresponde a §1.3.
- AC-04: No aparecen testimonios, cifras de clientes, logos de clientes, "sin tarjeta", "prueba gratis" ni "ganancia" sin el adjetivo "estimada". "Gratis" aparece solo junto a sus límites (1 producto, 2 ventas, 2 gastos).
- AC-09: El precio y los límites mostrados coinciden con el §1.6 y con lo que el producto aplica el día de publicación (ver Q13).
- AC-05: La sección de FAQ responde las preguntas de §7 marcadas "Incluir" y declara explícitamente lo que no se hace.
- AC-06: Navegable por teclado, foco visible, un único `h1`, contraste WCAG AA verificado con herramienta (el `#1677FF` sobre blanco es ≈3,9:1: no usarlo para texto pequeño; ver DDR branding).
- AC-07: A 390 px no hay scroll horizontal y el CTA es alcanzable en ≤1 toque desde cualquier punto (cabecera fija).
- AC-08: Los datos de ejemplo en imágenes están rotulados como ejemplo y son ficticios.

---

## 7. Dudas a responder para generar confianza

| # | Duda de la persona | Respuesta honesta propuesta | Estado |
|---|---|---|---|
| T1 | ¿Cuánto cuesta? ¿Qué incluye lo gratis? | Gratis: 1 producto, 1 cliente, 2 ventas y 2 gastos, con dashboard y reportes. Pro: Bs 30 al mes o Bs 350 al año, sin restricciones. | Incluir |
| T2 | ¿Mis datos se mezclan con los de otros negocios? | No: cada empresa ve solo sus datos; el servidor filtra por empresa. | Incluir |
| T3 | ¿Funciona en mi celular? ¿Debo instalar algo? | Es una web: se usa desde el navegador del celular, sin instalar. Funciona en celular (confirmado por el usuario). | Incluir |
| T13 | ¿Qué pasa cuando llego al límite del plan gratis? ¿Pierdo mis datos? | No puedes ingresar más datos hasta el día siguiente o hasta pasar a Pro; **tus datos siguen visibles** (Q17). | Incluir |
| T14 | ¿Cómo pago? | **Sin respuesta honesta posible hoy**: no hay forma de pagar (Q18, Q21). Si la landing menciona Pro, debe decir que el pago aún no está disponible o no mencionar compra. | Bloquea publicación |
| T15 | ¿Qué pasa si no renuevo Pro? | La cuenta se bloquea hasta que se realice el pago (Q20). Alcance del bloqueo pendiente (Q21). | Incluir tras Q21 |
| T4 | ¿Puedo agregar a mi equipo? | Hoy no hay alta de usuarios desde la pantalla; los agrega un admin con ayuda del equipo del producto. No prometer trabajo en equipo. | Incluir |
| T5 | ¿Emite facturas? ¿Lleva inventario o contabilidad? | No. Es control de pedidos, cobros y gastos. | Incluir |
| T6 | ¿La "ganancia" es real? | Es **estimada**: ventas − gastos registrados; no incluye costo de producción. | Incluir |
| T7 | ¿Puedo corregir un error? | Pedidos: se editan hasta "listo" y se cancelan con motivo; gastos: se editan o anulan. **Los pagos registrados no se pueden corregir todavía.** | Incluir (decidir tono) |
| T8 | ¿Qué pasa si olvido mi contraseña? | Hoy no hay recuperación automática. Decidir si se declara o se resuelve antes de publicar. | Q3 |
| T9 | ¿Puedo sacar mis datos (Excel/PDF)? | Aún no hay exportación. | Incluir |
| T10 | ¿Quién está detrás y cómo los contacto? | **Pendiente**: no hay datos de contacto ni equipo en el repo. | Q6 |
| T11 | ¿Qué hacen con mis datos? ¿Hay términos y privacidad? | **Pendiente**: no existen documentos. | Q4 |
| T12 | ¿Es un producto terminado? | Está en construcción; si se desea, decirlo con transparencia ("versión inicial"). | Decidir (Q8) |

---

## 8. Preguntas pendientes

### Resueltas
- **Q1. Precio/modelo:** Bs 30 base + plan gratuito limitado (§1.6).
- **Q2. Móvil:** funciona en celular, según el usuario (§1.6).

### Bloquean la publicación (no el diseño visual)
- **Q13. Implementación de planes:** el producto no aplica hoy límites ni cobro. Hace falta una task aparte (plan por empresa; límites diarios de 2 ventas y 2 gastos y 1 producto; mensaje al llegar al límite; botón de actualización; activación manual del plan). ¿Se hace antes de publicar la landing, o la landing sale sin sección de planes? Sin esto, la página promete algo que no ocurre. **Nota de impacto:** el límite diario cambia el flujo de pedidos, gastos y catálogo en backend (rechazar altas, mensaje claro, tests de frontera); afecta autorización y base de datos, por lo que probablemente requiere `delivery-architect`.
- **Q4. Legal:** ¿habrá términos y privacidad antes de abrir el registro público? Con un plan de pago, además, hacen falta condiciones de cobro. Hoy el registro es público (throttle 5/hora).

### Resueltas el 2026-10-12 (ver §1.6)
- **Q11:** Bs 30 al mes; Bs 350 al año.
- **Q12:** productos, ventas y gastos ilimitados.
- **Q14:** al llegar al límite no se pueden ingresar más datos; esperar al día siguiente o actualizar el plan.
- **Q15:** transacción = registro de una venta o de un gasto.
- **Q16:** sin pasarela por ahora; debe existir un botón que inicie la transacción.

### Decisiones del usuario del 2026-10-13
- **Q7, rutas [Confirmado por el usuario]:** la **raíz `/`** carga la landing; el producto vive bajo **`/pocketbiz/`**: `/pocketbiz/login`, `/pocketbiz/signup` y `/pocketbiz/**` para todo lo demás (dashboard, catálogo, clientes, pedidos, gastos, reportes). Hoy las rutas son `/authentication/signin`, `/authentication/signup`, `/dashboard/main`, etc.; el cambio es un **renombrado de rutas de toda la aplicación**, no solo agregar una página.
- **Q13 y Q21, planes y contratación: se ignoran.** La sección "Planes" se muestra **solo como información**, tal como está en la spec (Gratis con CTA "Empezar gratis"; Pro sin botón de compra, con "Pago disponible próximamente"). No se implementan límites ni cobro en esta entrega. Riesgo aceptado: la página describe límites que el producto aún no aplica.
- **Q4, términos y privacidad:** aún no definidos. La landing y el pie **no** llevan enlaces legales ni de contacto hasta que existan; el registro público sigue abierto.

### Resueltas el 2026-10-12 (segunda ronda)
- **Q17:** los límites son del plan gratuito; la persona sigue viendo sus datos; Pro no tiene restricciones.
- **Q18:** de momento nada; la pasarela de pagos es un tema pendiente.
- **Q19:** plan gratis: 1 cliente y acceso a su dashboard y reportes de ingresos y egresos.
- **Q20:** al vencer, se bloquea hasta que se realice el pago.

### Abiertas
- **Q21. Bloqueo sin forma de pagar:** si el plan Pro vence y se bloquea "hasta el pago", pero no hay pasarela ni acción de compra, **nadie puede contratar ni renovar hoy**. ¿Pro se ofrece solo como "próximamente"? ¿La activación será manual (transferencia + admin)? ¿"Bloquea" significa sin acceso alguno o solo lectura como el gratis? Define la tarjeta Pro y la FAQ T15.
- **Q22. Nombre del plan:** "Base" (antes) vs. "**Pro**" (último mensaje). Se asume Pro.
- **Q23. Frecuencia del límite gratuito:** "esperar al día siguiente" sugiere un tope **diario** de 2 ventas y 2 gastos; no fue confirmado de forma explícita. ¿Producto y cliente únicos son 1 en total (sin renovación)? ¿El "día" es la fecha local del servidor (`TIME_ZONE`)? ¿Cuenta por fecha de registro o por la fecha de la venta/gasto?
- **Q24. Nombres de reportes:** el producto muestra "ventas" y "gastos" y "ganancia estimada"; el usuario dice "ingresos y egresos". La landing usa los nombres del producto salvo que se indique lo contrario.

### No bloquean el diseño (suposiciones explícitas)
- **Q3. Contraseña olvidada:** se asume que se declara en la FAQ hasta que exista recuperación.
- **Q5. Imágenes:** se asume capturas reales del panel con datos ficticios (o ilustración propia), no stock con personas.
- **Q6. Contacto:** se asume un correo/WhatsApp de soporte a definir por el usuario; si no existe, el pie no lleva contacto.
- **Q7. Ubicación técnica:** hoy `/` redirige a `/authentication/signin`; la landing necesita una ruta pública (por ejemplo `/` o `/inicio`) fuera de `AuthGuard`, o un sitio aparte. Decisión para plan/arquitectura.
- **Q8. Etapa del producto:** se asume lenguaje neutro (sin "beta" ni "completo") hasta que el usuario decida.
- **Q9. Alcance geográfico y moneda:** se asume Bolivia/Bs solo en los ejemplos; no se afirma cobertura de países ni multimoneda.
- **Q10. Idioma:** solo español (la plantilla trae en/es/de en el menú, no se pide más).

---

## 9. Contradicciones y riesgos detectados
- **Eslogan vs. capacidades:** "en el bolsillo" sugiere app móvil; el producto es web sin PWA. Mitigación: usar "desde el navegador de tu celular" y no usar "app" ni "descarga".
- **Oferta comercial no implementada:** precio y límites existen solo como decisión de negocio; el producto no los aplica (Q13). Publicar la landing así crearía una promesa que no se cumple y, con un plan gratis sin límite técnico, nadie tendría motivo para pagar.
- **Pro que se bloquea y no se puede pagar:** el vencimiento bloquea la cuenta hasta el pago, pero no hay mecanismo de pago (Q21). Ofrecer Pro en la landing sin esto es una promesa que nadie puede cumplir ni cobrar.
- **Límite gratuito muy bajo (1 producto, 1 cliente, 2 ventas, 2 gastos):** puede impedir ver el valor del resumen, que es lo más atractivo del producto, con 2 ventas y 2 gastos. Es decisión de negocio; sugerencia no vinculante: mostrar en la landing un resumen de ejemplo rotulado como tal.
- **Nombre del repo vs. marca:** repo y docs dicen "dore-mini-erp"; la marca pública es PocketBiz. Usar solo PocketBiz en la landing.
- **"Ganancia":** el requerimiento dice "controlar ventas y gastos"; `ddd.md` exige "ganancia estimada". La landing debe respetarlo siempre.
- **Registro público sin términos ni recuperación de contraseña:** riesgo de confianza y soporte; ver Q3 y Q4.
- **Público inferido:** sin entrevistas; el mensaje del problema (sección 2) es la parte más débil de la evidencia.

---

## 10. Entrega a la siguiente etapa
- Para `delivery-design-system`: reutilizar tokens de marca existentes (DDR branding); la landing necesita solo componentes de marketing (hero, tarjetas de beneficio, pasos, FAQ/acordeón, bloque CTA), no los del panel.
- Para `delivery-ui-design` (Stitch): la conexión ya funciona y no hay proyecto; crear el de PocketBiz y generar 1 propuesta desktop (1440) y 1 móvil (390). Contenido de §5 como fuente de textos; datos ficticios rotulados. La sección "Planes" puede diseñarse con los datos de §1.6, marcando como pendientes Q11–Q12.
- Pendiente de decisión del usuario antes de implementar: Q13 (implementar planes), Q4, Q7 y, para cerrar la tarjeta Pro, Q21 (cómo se contrata/renueva y alcance del bloqueo). Q22–Q24 se resuelven con supuestos explícitos.
