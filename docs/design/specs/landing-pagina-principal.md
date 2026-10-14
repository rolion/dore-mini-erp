# Especificación de pantalla — Landing PocketBiz

**Módulo:** landing · **Pantalla:** página principal pública
**Estado de revisión:** propuesto (sin aprobación del usuario)
**Fecha:** 2026-10-12
**Fuentes:** `docs/design/ux-brief.md` (§1.6, §4, §5, §6, §7), `docs/design/design-system.md`, `docs/design/DDR-pocketbiz-branding-logos-marca-y-color.md`.
**Referencia visual:** Stitch, proyecto `10435969640252772563` (ver `docs/design/screens.md` y su estado real de verificación). Esta especificación es la fuente de contenido; si la referencia de Stitch difiere, prevalece este documento.

Esta pantalla **no existe** en el código. Ruta pública pendiente de decisión (ux-brief Q7).

---

## 1. Objetivo y acción principal
- **Objetivo:** que la persona cree su cuenta.
- **Acción principal:** "Empezar gratis" → `/authentication/signup`.
- **Secundaria:** "Iniciar sesión" → `/authentication/signin`; anclas internas.
- Un solo CTA primario visible por sección; el CTA se repite en cabecera, hero, plan gratuito y cierre.

## 2. Datos
Contenido estático. Sin llamadas a la API. Las cifras ilustrativas llevan la etiqueta visible **"Ejemplo"**.

**Capturas reales de la aplicación (aportadas por el usuario, 2026-10-13)**, guardadas en `docs/design/exports/landing/referencias-producto/`. Sustituyen a las maquetas inventadas:

| Archivo | Muestra | Datos visibles |
|---|---|---|
| **`dashboard-movil-403-positivo.png` (403×850) — vigente en el hero** | Dashboard en móvil: selector Hoy / Esta semana / Este mes / Rango, "Actualizar", tarjetas Ventas, Gastos, Ganancia estimada, Pedidos | Ventas `Bs 280.50`, Gastos `Bs 270.00`, Ganancia estimada `Bs 10.50` (en verde), 4 pedidos, ticket promedio `Bs 70.13` |
| `dashboard-movil-396.png` (396×858) — reemplazada | Misma pantalla, versión anterior | Ventas `Bs 252.50`, Ganancia estimada `Bs -17.50` (rojo), 3 pedidos, ticket `Bs 84.17` |
| `nuevo-pedido-canal-de-venta.png` (1914×946) | Formulario "Nuevo pedido": Cliente, **Canal de venta** (WhatsApp), Fecha del pedido, Entrega prevista, Notas | Cliente "Joe Doe"; barra lateral con usuario "oleon" y "Empresa por defecto" |
| `pedido-listo-entrega-pendiente.png` (1893×943) | Detalle del pedido: Entrega "Listo" (entrega prevista 14/10/2026) y Cobro "Pendiente", `Saldo Bs 28.00`; acciones "Marcar entregado" y "Cancelar pedido" | Pedido `P-A614429A`, producto "cuñape cebollita" |
| `pedido-entregado-pagado.png` (1897×945) | Mismo pedido: Entrega "Entregado" (real 13/10/2026) y Cobro "Pagado", "Sin saldo" | Pagado `Bs 28.00 de Bs 28.00` |

Son datos de una instancia de desarrollo. Reglas de uso:
- Rotular cada captura "Captura de la aplicación con datos de ejemplo".
- Recortar la barra lateral (usuario "oleon", "Empresa por defecto") y el cabezal; mostrar solo las tarjetas relevantes.
- Mantener el formato monetario **real del producto** (`Bs 28.00`, punto decimal), no el `Bs 1.200,00` usado antes en este documento y en `design-system.md`.
- No añadir cifras inventadas por encima de lo que muestran las capturas.

## 3. Layout (desktop 1440 px · contenedor 1200 px · 12 columnas, gutter 24 px)

| # | Bloque | Contenido y disposición |
|---|---|---|
| 0 | Cabecera fija (64 px) | Izq.: `main-logo`/wordmark. Centro: anclas "Qué puedes controlar", "Cómo funciona", "Planes", "Preguntas". Der.: enlace "Iniciar sesión" y botón primario "Empezar gratis". |
| 1 | Hero | Col. 1–6: `h1` "Tu negocio en el bolsillo"; subtítulo "Registra tus pedidos, cobros y gastos en un solo lugar y mira de un vistazo cuánto vendiste, qué te deben y qué tienes que entregar."; CTA "Empezar gratis"; nota "Plan gratuito con límites: 1 producto, 1 cliente, 2 ventas y 2 gastos por día." Col. 7–12: **un teléfono** (marco genérico, sin marca de fabricante) que contiene la captura `dashboard-movil-403-positivo.png`, rotulada "Captura con datos de ejemplo" (ver §3.1). |
| 2 | Reconocimiento *(hipótesis)* | Título "¿Tus ventas viven en chats, cuadernos y de memoria?" y 3 frases cortas. Sin cifras. Eliminable si no se valida. |
| 3 | Qué puedes controlar | 4 tarjetas (3 col. c/u): **Pedidos y entregas** (estados y canal: WhatsApp, Facebook, Instagram, venta directa, feria) · **Cobros** (pagos parciales y saldo pendiente) · **Gastos** (por categoría y método de pago) · **Clientes y productos** (historial de compras, precios, activar o desactivar). |
| 4 | Entrega y pago, por separado | Título "Entrega y pago, por separado". Subtítulo "Cada pedido guarda su canal de venta, y su entrega y su cobro se siguen por separado." Secuencia de **3 pasos** con capturas reales (ver §3.2). |
| 5 | Tu resumen | Selector Hoy / Esta semana / Este mes / Rango (solo ilustrativo); tarjetas Ventas, Gastos y **"Ganancia estimada"** con nota "Ventas − gastos registrados. Es una estimación, no la utilidad contable." Rótulo "Ejemplo". |
| 6 | Cómo empezar | 3 pasos numerados: 1 Crea tu cuenta con el nombre de tu empresa · 2 Registra tus productos, clientes y tu primer pedido · 3 Mira tu resumen. |
| 7 | Planes | Selector Mensual/Anual. Tarjeta **Gratis** y tarjeta **Pro** (ver §5). |
| 8 | Tus datos, tu empresa | "Cada empresa ve solo sus datos." Sin afirmar certificaciones ni cifrado específico. |
| 9 | Preguntas frecuentes | Acordeón (ver §6). |
| 10 | Cierre | "Empieza a ver tu negocio con claridad" + "Empezar gratis" + enlace "Iniciar sesión". |
| 11 | Pie | Wordmark y "Iniciar sesión". Contacto y legales solo cuando existan (Q4, Q6). |

### 3.1 Hero con teléfono
- **Marco:** CSS puro, genérico (sin logotipos ni modelo comercial reconocible): ancho 280–300 px en desktop, borde/bisel 10 px `#16192A`, radio exterior 36 px, radio de pantalla 28 px, sombra suave; sin ranura de cámara obligatoria. El marco es decorativo (`aria-hidden`); la imagen interna lleva su `alt`.
- **Contenido:** `dashboard-movil-403-positivo.png` tal cual (403×850, proporción ≈ 0,474), sin recorte ni distorsión, anclada arriba; no se hace scroll dentro del marco.
- **Posición:** texto a la izquierda y teléfono a la derecha en desktop; en móvil, texto primero y teléfono centrado debajo (≈ 260 px de ancho).
- **Rótulo:** "Captura de la aplicación con datos de ejemplo" bajo el teléfono, en `text-muted` 12–14 px.
- **Alt sugerido:** "Panel de PocketBiz en el celular: ventas, gastos y ganancia estimada del mes".
- **Evidencia:** la captura demuestra que el dashboard se adapta a un ancho ≈ 396 px (confirma Q2 con una imagen real aportada por el usuario).
- **Contenido (resuelto 2026-10-13):** el usuario sustituyó la captura con ganancia negativa por una con **Ganancia estimada `Bs 10.50`** (verde), Ventas `Bs 280.50`, Gastos `Bs 270.00`, 4 pedidos y ticket promedio `Bs 70.13`. No alterar las cifras de la imagen.

### 3.2 Entrega y pago, por separado (secuencia)
Contenedor de 1200 px; cada paso es una tarjeta con número, título, una línea de texto y una captura **recortada** (sin barra lateral):

| Paso | Título | Texto | Captura (recorte aproximado, px de origen) |
|---|---|---|---|
| 1 | Registras el pedido y su **canal de venta** | "WhatsApp, Facebook, Instagram, venta directa, feria u otro: cada pedido guarda de dónde vino." | `nuevo-pedido-canal-de-venta.png`, formulario: x 283–1889, y 155–680 |
| 2 | Pedido listo, **entrega pendiente** | "El pedido está listo y todavía no se entrega. Ves el saldo por cobrar." | `pedido-listo-entrega-pendiente.png`, tarjetas Entrega y Cobro: x 222–1876, y 113–292 |
| 3 | **Entregado y pagado** | "Cuando se entrega y se cobra, el pedido queda sin saldo. Entrega y pago se siguen por separado." | `pedido-entregado-pagado.png`, tarjetas Entrega y Cobro: x 225–1879, y 100–280 |

- **Canal de venta:** se enuncia como funcionalidad real (selector "Canal de venta", obligatorio en el formulario); los valores son los de `ddd.md`/Pedidos: WhatsApp, Facebook, Instagram, venta directa, feria, otro.
- **Etiquetas de estado** visibles en la captura ("Listo", "Pendiente", "Entregado", "Pagado", "Sin saldo") deben coincidir con el texto de los pasos; no renombrarlas.
- **Pago parcial:** esta secuencia no muestra pago parcial; si se menciona en tarjetas, es por la funcionalidad (ux-brief §1.2), no por estas imágenes.
- **Ancho de lectura:** los recortes de 1650 px de ancho se muestran a 1200 px (≈ 0,73×); el texto de la interfaz (≈ 10–14 px) queda en ≈ 7–10 px. Si no es legible en la revisión, usar recortes por tarjeta (Entrega / Cobro por separado, ≈ 820 px de origen) o capturas nuevas a 1200 px de ancho.

### Móvil (390 px, una columna, gutter 16 px)
- Cabecera: logo `simple-logo` o wordmark, botón "Empezar gratis" compacto y menú (hamburguesa) con las anclas e "Iniciar sesión".
- Hero: texto antes que el teléfono (≈ 260 px de ancho, centrado); CTA ancho completo (≥44 px de alto).
- Tarjetas y pasos apilados.
- **Entrega y pago:** las capturas de escritorio (1650 px) a 358 px de ancho quedan ilegibles (≈ 0,22×). No usarlas tal cual. Opciones: (a) capturas nuevas del detalle del pedido a 390 px (recomendado; el producto funciona en móvil), (b) una recreación en HTML de las dos tarjetas de estado con los mismos textos y tokens. Decisión pendiente (Q25).
- Planes: tarjetas apiladas, Gratis primero.
- Barra inferior fija opcional con el CTA primario (decisión de UI; no oculta contenido ni foco).

## 4. Componentes (sobre `design-system.md`)
| Componente | Origen | Nota |
|---|---|---|
| Botón primario/secundario/enlace | Existente (plantilla) | 42 px, radio 8 px; texto blanco sobre `#1677FF` mide 4,10:1: peso 500+ y ≥16 px en CTAs |
| Tarjeta de beneficio | Nuevo (landing) | icono + título + texto |
| Pasos numerados | Nuevo (landing) | número en círculo `#1677FF` |
| Tarjeta de plan | Nuevo (landing) | selector Mensual/Anual con `aria-pressed` |
| Acordeón | Existente (`ngb-accordion` de la plantilla) | un panel abierto por vez opcional |
| Marco de teléfono | Nuevo (landing) | CSS genérico; decorativo; contiene `dashboard-movil-396.png` |
| Tarjeta de captura con paso | Nuevo (landing) | número, título, texto, imagen recortada con `alt` y rótulo de datos de ejemplo |
| Badge de estado | Existente | texto + icono, nunca solo color |

## 5. Planes (contenido)

| | Gratis | Pro |
|---|---|---|
| Precio | Bs 0 | **Bs 30 al mes** · **Bs 350 al año** (selector) |
| Productos | 1 | Sin restricciones |
| Clientes | 1 | Sin restricciones |
| Ventas | 2 por día | Sin restricciones |
| Gastos | 2 por día | Sin restricciones |
| Dashboard y reportes de ventas y gastos | Incluidos | Incluidos |
| Al llegar al límite | Sigues viendo tus datos y puedes registrar de nuevo al día siguiente | — |
| Acción | **"Empezar gratis"** → `/authentication/signup` | **Sin botón de compra**: etiqueta "Pago disponible próximamente" |

Reglas:
- "Gratis" siempre junto a sus límites.
- El plan anual (Bs 350) ahorra Bs 10 frente a 12 × Bs 30 = Bs 360: no destacarlo como descuento.
- El texto "por día" depende de Q23 (límite diario supuesto); confirmar antes de publicar.
- "Pro" supone confirmación de Q22.
- La sección completa depende de que el producto aplique planes y límites (Q13) y de Q21.

## 6. Preguntas frecuentes (texto)
| Pregunta | Respuesta |
|---|---|
| ¿Necesito instalar algo? | Es una web: se usa desde el navegador del celular o de la computadora. |
| ¿Emite facturas o lleva inventario? | No. Es control de pedidos, cobros y gastos. |
| ¿La ganancia es real? | Es estimada: ventas menos gastos registrados; no incluye el costo de producción. |
| ¿Puedo agregar a mi equipo? | Hoy no se hace desde la pantalla. |
| ¿Qué pasa si olvido mi contraseña? | Aún no hay recuperación automática. |
| ¿Qué pasa al llegar al límite del plan gratuito? | No puedes ingresar más datos hasta el día siguiente o hasta pasar a Pro; tus datos siguen visibles. |
| ¿Puedo sacar mis datos? | Aún no hay exportación. |

## 7. Interacciones
- Anclas: desplazamiento suave a la sección; respetar `prefers-reduced-motion`.
- Cabecera fija: no cubre el foco ni el título de la sección destino (`scroll-margin-top` ≥ altura de cabecera).
- Selector Mensual/Anual: cambia el precio mostrado; no persiste.
- Acordeón: Enter/Espacio abre y cierra; `aria-expanded`.
- Enlaces CTA: navegación normal (no ventana nueva).

## 8. Validación
No hay formularios en la landing. La validación ocurre en `/authentication/signup`.

## 9. Permisos y estados
| Estado | Comportamiento |
|---|---|
| Visitante anónimo | Página completa. |
| Con sesión activa | CTA y cabecera muestran "Ir a mi panel" → `/dashboard/main`; sin redirección forzada. |
| Registro deshabilitado (`REGISTRATION_ENABLED=False`) | Sin CTA de registro; mensaje "El registro no está disponible por ahora" e "Iniciar sesión". Requiere que el frontend conozca el estado (decisión de arquitectura). |
| Carga | Contenido estático; imágenes con dimensiones reservadas. |
| Error de imagen | Texto alternativo visible; la página sigue usable. |
| Sin JavaScript | Contenido legible; acordeón abierto (mejora progresiva). |

## 10. Accesibilidad
- Un único `h1`; jerarquía `h2` por sección; `nav` con `aria-label`.
- Foco visible: anillo 3 px `#1677FF` al 35 %; orden de tabulación = orden visual.
- Contraste: texto azul pequeño `#0958D9`; no usar `#98A6AD`; estados con texto e icono.
- Objetivos táctiles ≥ 44 × 44 px en móvil.
- Imágenes informativas con `alt`; maqueta "Ejemplo" con texto alternativo descriptivo.

## 11. Criterios de aceptación
- **AC-L01:** el hero muestra "Tu negocio en el bolsillo" y el CTA "Empezar gratis" sin hacer scroll en 1440×900 y 390×844.
- **AC-L02:** todo CTA primario navega a `/authentication/signup`; "Iniciar sesión" a `/authentication/signin`.
- **AC-L03:** cada funcionalidad nombrada corresponde a una fila de ux-brief §1.2; ninguna a §1.3.
- **AC-L04:** no hay testimonios, cifras de clientes, logos de clientes, "sin tarjeta" ni "prueba gratis"; "gratis" aparece junto a sus límites.
- **AC-L05:** la tarjeta Pro no contiene botón de compra mientras no exista flujo de pago.
- **AC-L06:** "ganancia" aparece siempre como "Ganancia estimada" con su nota.
- **AC-L07:** las cifras ilustrativas llevan "Ejemplo".
- **AC-L08:** a 390 px no hay scroll horizontal; CTA alcanzable sin scroll en la cabecera.
- **AC-L09:** navegable por teclado, un solo `h1`, contraste AA verificado con herramienta para texto pequeño.
- **AC-L10:** precio y límites coinciden con ux-brief §1.6 y con lo que el producto aplique el día de publicación.
- **AC-L11:** la sección "Planes" no se publica sin resolver Q13 y Q21.
- **AC-L12:** el hero muestra la captura del dashboard dentro de un marco de teléfono, sin recortar ni deformar, con su rótulo de datos de ejemplo y `alt` descriptivo.
- **AC-L13:** la sección "Entrega y pago, por separado" muestra la secuencia de 3 pasos y enuncia el **canal de venta** (paso 1) con los valores reales del producto.
- **AC-L14:** ninguna captura muestra la barra lateral con usuario o empresa; los textos de la interfaz visibles en cada captura son legibles (o se usa la alternativa móvil de Q25).
- **AC-L15:** los importes de la landing usan el formato del producto (`Bs 28.00`) y ninguna cifra supera lo que aparece en las capturas.

## 12. Decisiones del 2026-10-13 y dependencias abiertas
- **Rutas (Q7):** `/` = landing; `/pocketbiz/login`, `/pocketbiz/signup`, `/pocketbiz/**` = aplicación. Los CTA de la landing apuntan a `/pocketbiz/signup` (primario) y `/pocketbiz/login` (secundario); "Ir a mi panel" a `/pocketbiz/dashboard/main`. Esto reemplaza las rutas `/authentication/*` y `/dashboard/*` citadas en §1 y §9 de este documento.
- **Planes (Q13, Q21):** ignorados; sección informativa, sin botón de compra en Pro.
- **Legales (Q4):** sin enlaces hasta que existan.

Pendientes originales:
Q4 (términos y privacidad), Q7 (ruta pública), Q13 (implementar planes), Q21 (contratación/renovación y alcance del bloqueo), Q22 (nombre "Pro"), Q23 (límite diario), **Q25** (capturas móviles o recreación para la secuencia de entrega y pago; conservar o cambiar la captura con ganancia negativa).

## 13. Historial de cambios
| Fecha | Cambio | Origen |
|---|---|---|
| 2026-10-12 | Primera versión | delivery-ui-design |
| 2026-10-13 | Hero: imagen del dashboard dentro de un teléfono (§3.1). Sección Entrega y pago: secuencia de 3 pasos con capturas reales y mención del canal de venta (§3.2). Datos ficticios sustituidos por los de las capturas (§2). Selector con "Rango". Criterios AC-L12..L15. | Solicitud del usuario (`/delivery-design`) con 4 capturas |

| 2026-10-13 | Captura del hero sustituida por `dashboard-movil-403-positivo.png` (ganancia positiva). Referencia en Stitch regenerada en 4 pantallas con la versión del teléfono; desviaciones H1–F2 en `screens.md`. | Solicitud del usuario con captura nueva |

| 2026-10-13 | "Qué puedes controlar" regenerada (`358c02db…`) y versión móvil generada en 4 pantallas (`190b408d…`, `1c04e674…`, `42795c5f…`, `4ce1f664…`). Subtítulo de "Qué puedes controlar": "Pedidos, cobros, gastos, clientes y productos, en un solo lugar." Observaciones M1–M6 en `screens.md`. | Solicitud del usuario |

**Referencia móvil (Stitch):** hero `190b408d…` (viewport 390), y tres pantallas de columna ≈400 px en lienzo 1440 (`1c04e674…`, `42795c5f…`, `4ce1f664…`). Faltan "Cómo empezar" en móvil, el orden Resumen → Cómo empezar → Planes y el selector de periodo en "Tu resumen".

**Referencia visual vigente (Stitch, proyecto `10435969640252772563`):** hero `087ff272…`, entrega y pago `3d02b991…`, resumen y planes `567d596c…`, finales `a6164829…` (las versiones `5e57d193…`, `3149862f…` y `e201288a…` quedaron reemplazadas tras corregir las desviaciones altas). Todas **propuestas**, revisadas visualmente solo en desktop light. Esta especificación prevalece donde difieran; los datos del teléfono en Stitch son una recreación y deben sustituirse por la captura real. Pendientes: "Qué puedes controlar" en la versión con teléfono, estado Anual de Planes, móvil 390 y dark.
