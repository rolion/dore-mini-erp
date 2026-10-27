# Revisión visual — Landing PocketBiz

**Fecha:** 2026-10-13 · **Etapa:** `delivery-visual-review` · **Estado:** solo revisión (no se aplicaron correcciones)
**Alcance:** referencias de Stitch de la landing (`docs/design/screens.md`) contra `docs/design/specs/landing-pagina-principal.md`, `docs/design/design-system.md` y `docs/design/ux-brief.md`.
**No es** una aprobación del usuario.

## 1. Cobertura real

| Comprobación | Estado |
|---|---|
| Referencia vigente recuperada por MCP y exportada (capturas a 1440 px y 780 px) | **Hecho** (ver `docs/design/exports/landing/`) |
| Inspección visual de las referencias | **Hecho**, desktop light y hero móvil |
| **Comparación referencia ↔ aplicación en ejecución** | **No verificado**: la landing **no está implementada** (no hay ruta pública ni componente; `/` redirige al login). No se ejecutó la aplicación |
| Contraste por medición de píxeles sobre las capturas | **Hecho con salvedad** (ver §3) |
| Tema dark | **No verificado**: no existe referencia dark |
| Móvil 390 px real | **Parcial**: solo el hero móvil es un viewport real; las otras 3 son una columna de ≈400 px en un lienzo de 1440 |
| Teclado, foco visible, labels, overflow | **No verificado**: son capturas estáticas; no se ejecutó el HTML de Stitch |
| Estados (carga, error, sesión activa, registro deshabilitado) | **No verificado**: no hay referencia de esos estados |

## 2. Referencias revisadas

| Pantalla | ID | Viewport | Resultado |
|---|---|---|---|
| Hero v2 | `087ff272…` | 1440 desktop light | Con hallazgos |
| Qué puedes controlar | `358c02db…` | 1440 desktop light | Conforme en contenido |
| Entrega y pago v2 | `3d02b991…` | 1440 desktop light | Con hallazgos |
| Resumen, Cómo empezar y Planes v2 | `567d596c…` | 1440 desktop light | Con hallazgos |
| Datos, FAQ, cierre y pie | `a6164829…` | 1440 desktop light | Conforme en contenido |
| Hero móvil | `190b408d…` | 390 @2x | Con hallazgos |
| Móvil: controlar + entrega y pago | `1c04e674…` | columna ≈400 px | Con hallazgos |
| Móvil: planes + resumen | `42795c5f…` | columna ≈400 px | Con hallazgos |
| Móvil: datos, FAQ, cierre | `4ce1f664…` | columna ≈400 px | Conforme en contenido |

## 3. Mediciones (método)
Se muestreó el color de fondo y el píxel **más oscuro** de una región de texto en cada captura y se calculó la razón de contraste WCAG 2.x. **Salvedad:** el antialiasing y el renderizado subpíxel desvían el color en textos finos; los valores sobre textos de 12–14 px son orientativos. Los fondos y botones se leen con exactitud.

| Elemento | Valor medido | Esperado (token) | Contraste | Veredicto |
|---|---|---|---|---|
| Fondo de página (desktop) | `#F6F6F6` | `#F6F6F6` | — | Conforme |
| CTA "Empezar gratis" (desktop y móvil) | `#1677FF` | `#1677FF` | blanco/primario **4,10:1** | Ver F-01 |
| Texto muted en móvil (nota de límites) | `#6C757D` | `#6C757D` | **4,34:1** sobre `#F6F6F6` | **Falla AA** (F-02) |
| Pie de foto del teléfono (móvil) | `#69727A` | `#6C757D` | 4,53:1 | Límite |
| Saldo en rojo (Entrega y pago) | `#C70000` | `#C62828` | 6,13:1 sobre blanco | Conforme |
| Badge "Listo" | `#006700` sobre `#E6F7ED` | `#2F8F46` | 6,43:1 | Conforme (Stitch usó un verde más oscuro que el token) |
| Badge "Pendiente" | `#CD6D00` sobre `#FFFBE6` | `#B45309` | **3,49:1** | **Falla AA** (F-03) |
| Párrafos muted (desktop) | no concluyente | `#6C757D` | n/d | No verificado (valores desviados por antialiasing) |

## 4. Hallazgos

Tipos: **FV** fallo visual/de contenido · **A11Y** accesibilidad medida · **DS** defecto del sistema de diseño · **MEJ** mejora opcional · **LIM** limitación.

| # | Sev. | Tipo | Pantalla | Esperado | Observado | Evidencia | Acción propuesta |
|---|---|---|---|---|---|---|---|
| F-01 | Media | A11Y | Todas (CTA) | Texto de botón ≥ 4,5:1 o ≥ 18,66 px en negrita | Blanco sobre `#1677FF` = 4,10:1 con texto de 15–16 px, peso 500 | Medido; `design-system.md` §2.1, D3 | Usar primario `#0958D9` (6,16:1) en botones con texto pequeño, o texto ≥ 18,66 px en negrita (CTA de hero). Decisión de marca del usuario |
| F-02 | Media | A11Y / DS | Hero, Resumen, móvil | Texto secundario ≥ 4,5:1 | `#6C757D` sobre el fondo `#F6F6F6` = **4,34:1** (sobre blanco 4,69:1). Afecta notas, subtítulos y pie de foto de 12–14 px | Medido (móvil) | Cambiar `text-muted` a ≈ `#5F6870` (5,25:1) en fondos `#F6F6F6`, o poner el texto muted solo sobre blanco. Actualizar `design-system.md` |
| F-03 | Media | A11Y | Entrega y pago v2 (paso 2) | Texto de badge ≥ 4,5:1 | "Pendiente" `#CD6D00` sobre `#FFFBE6` = 3,49:1, 12 px | Medido | Usar `warning-text` `#B45309` (4,72:1 sobre `#FFF7E8`) |
| F-04 | Media | DS | Sistema de diseño | Pares de token ≥ 4,5:1 | `success-text` `#2F8F46` sobre su fondo de badge `#E8F8EC` = **3,71:1** (sobre blanco 4,09:1). Defecto de **mi** propuesta de tokens | Cálculo | Cambiar a `#1F7A3A` (4,89:1) y actualizar `design-system.md` §2.1 |
| F-05 | Alta | FV | Hero v2, Planes v2, móvil | El logo real (`main-logo.png`/`simple-logo.png`) | Icono de casa en el hero, toldo en planes y móvil; ninguno es el logo | Capturas | En implementación usar los logos del repo. En Stitch no hay forma de subirlos con las herramientas expuestas |
| F-06 | Media | FV | Hero v2 / móvil | Captura real del dashboard dentro del teléfono | Recreación con diseño propio de Stitch (campana en móvil, icono de caja en Pedidos) | Capturas | Sustituir por `dashboard-movil-403-positivo.png` en implementación; no tratar la maqueta como funcionalidad |
| F-07 | Media | FV | Hero móvil | Pestañas del dashboard legibles | "Esta semana" y "Este mes" parten en dos líneas dentro del teléfono | Captura 780×1768 | Con la captura real queda resuelto (tiene su propio layout) |
| F-08 | Media | FV | Móvil (3 pantallas) | Viewport de 390 px | Columna ≈400 px en un lienzo de 1440 | `screens.md` M4 | Regenerar con viewport móvil real |
| F-09 | Media | FV | Móvil | Orden Resumen → Cómo empezar → Planes y selector de periodo | Planes antes que Resumen; falta "Cómo empezar"; falta selector de periodo | Capturas | Regenerar e incluir |
| F-10 | Media | FV | Planes v2 | Textos del producto ("Total de los pedidos del periodo") | "Salidas operativas registradas" en Gastos; nota de ganancia repetida (dentro de la tarjeta y debajo) | Captura | Eliminar el subtítulo inventado y la nota duplicada |
| F-11 | Baja | FV | Planes v2 | Sin relleno de marketing | "Sin configuraciones complejas ni curvas lentas…", "Para validar tu registro diario sin costo", "Operativa completa para negocios con mayor ritmo", "Control operativo adaptado a la etapa real de tu negocio" | Captura | Quitar o validar con el usuario |
| F-12 | Baja | MEJ | Hero, Entrega y pago, Qué puedes controlar | Espaciado vertical equilibrado | Márgenes superior e inferior excesivos en las secciones aisladas | Capturas | Normalizar al integrar la página completa |
| F-13 | Baja | FV | Datos (escritorio y móvil) | Icono neutro (sin sugerir seguridad certificada) | Escudo azul junto a "Tus datos, tu empresa" | Capturas | Cambiar a icono de empresa |
| F-14 | Baja | MEJ | Planes v2 | Pro con altura similar a Gratis | Gran espacio vacío bajo la única viñeta de Pro | Captura | Alinear alturas o reducir |
| F-15 | Media | LIM | Todas | Estados: sesión activa ("Ir a mi panel"), registro deshabilitado, anclas con scroll | Solo existe el estado anónimo | Spec §9 | Generar variantes o describirlas en el plan |
| F-16 | Media | LIM | Todas | Dark | No hay referencia dark | — | Decidir si la landing necesita dark (ux-brief: "no requerido") |

### Seguimiento de correcciones (2026-10-13)
| # | Estado | Detalle |
|---|---|---|
| F-02 | **Corregido en `design-system.md`** | Nuevo token derivado `text-muted-on-bg` `#5F6870` (5,25:1 sobre `#F6F6F6`); `#6C757D` queda solo para blanco. Falta aplicarlo en la referencia de Stitch (regeneración) y revisar el código del panel (D9) |
| F-04 | **Corregido en `design-system.md`** | `success-text` pasa de `#2F8F46` a `#1F7A3A` (4,89:1 sobre `#E8F8EC`). Falta reflejarlo en las pantallas de Stitch |
| Resto | Abiertos | F-01, F-03, F-05 a F-16 |

## 5. Conformidades verificadas
- Titular, subtítulo, CTA y nota de límites coinciden con la spec (hero desktop y móvil).
- Planes: Gratis y Pro con los límites y precios del ux-brief §1.6; **Pro sin botón de compra** con "Pago disponible próximamente".
- Entrega y pago v2: Entrega = Listo, Cobro = Pendiente, `Saldo Bs 28.00` (coincide con el producto); paso 3 Entregado/Pagado/Sin saldo.
- FAQ con las 6 preguntas y respuestas del ux-brief; pie mínimo (wordmark + Iniciar sesión) en las pantallas finales.
- Sin testimonios, cifras de clientes, "sin tarjeta" ni pie legal en las pantallas vigentes.
- Ganancia estimada en verde con la nota "Ventas − gastos registrados. Es una estimación, no la utilidad contable."
- Formato monetario `Bs 28.00`, igual al producto.

## 6. Resumen y recomendación
- **No hay fallos funcionales** (no hay aplicación que comparar).
- **Altos:** F-05 (logo inventado).
- **Medios:** F-01 a F-04 (contraste, de los cuales F-02 y F-04 son defectos del propio sistema de diseño), F-06 a F-10, F-15, F-16.
- **Antes de implementar:** corregir F-02 y F-04 en `design-system.md`, decidir F-01 con el usuario, regenerar la móvil (F-08, F-09) y tratar F-05/F-06 en la implementación con los assets reales.
- **Después de implementar:** repetir esta revisión comparando la app en 1440 y 390 px, light y (si se decide) dark, con pruebas de teclado y foco.

## 7. Evidencia
Capturas en `docs/design/exports/landing/` (sin credenciales ni URLs temporales). Las mediciones de §3 se calcularon sobre esos archivos.
