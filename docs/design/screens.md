# Registro de pantallas — PocketBiz (Stitch)

Registro conforme a `docs/design/stitch-workflow.md`. Estados de revisión: **propuesto** · **revisado** · **aprobado** (solo con aprobación explícita del usuario). Ninguna pantalla está aprobada.

## Proyecto
| Producto | Nombre | Project ID | Visibilidad | Creado |
|---|---|---|---|---|
| PocketBiz | PocketBiz | `10435969640252772563` | PRIVATE | 2026-10-12 |

## Design systems del proyecto (generado por Stitch, no por el repo)
| Nombre | Asset ID | Versión | Observación |
|---|---|---|---|
| PocketBiz Operational Admin | `7a057744e0f840e4ad8791d95acab9db` | 1 | Creado automáticamente por Stitch a partir de la primera generación; `designMd` conserva los tokens enviados en el prompt (ver desviaciones en `design-system.md` §11). No es fuente de verdad. |

## Pantallas
| Módulo | Pantalla | Viewport / tema | Estado UI | Project ID | Screen ID | URL devuelta | Fecha | Revisión |
|---|---|---|---|---|---|---|---|---|
| design-system | Componentes (guía de estilo) | Desktop 1440 / light | Hoja de componentes: botones, campos, badges, alertas, tabla, tarjetas de estadística | `10435969640252772563` | **no disponible** (`list_screens` devuelve `{}`; la respuesta de generación no incluyó el ID) | — (no se registra la URL temporal de la miniatura) | 2026-10-12 | propuesto — revisión visual limitada a miniatura 319×512 |

| landing | **Hero (cabecera + teléfono) — vigente v2** | Desktop 1440 / light | Hero con teléfono simplificado (Ventas Bs 280.50, Gastos Bs 270.00, Ganancia estimada Bs 10.50 en verde, Pedidos 4) | `10435969640252772563` | `087ff272caca470e8dc299b16c365115` | — | 2026-10-13 | **revisado visualmente** (1440×1024); desviaciones altas corregidas; ver "Correcciones" |
| landing | Hero v1 | Desktop 1440 / light | Con insignia, "sin tarjeta", barra inferior y pie inventados | `10435969640252772563` | `5e57d19307cf4f35b6081d4bd9437022` | — | 2026-10-13 | **reemplazada** por `087ff272…` |
| landing | **Entrega y pago, por separado — vigente v2** | Desktop 1440 / light | Secuencia de 3 pasos; Entrega=Listo, Cobro=Pendiente, Saldo Bs 28.00 | `10435969640252772563` | `3d02b991007a44e0abce090c8c96c5f1` | — | 2026-10-13 | **revisado visualmente** (1440×1152); E1 corregida |
| landing | Entrega y pago v1 | Desktop 1440 / light | "Listo" bajo "Preparación", "Pendiente" bajo "Entrega" | `10435969640252772563` | `3149862f249e46f6be68fbfe53ddc5f7` | — | 2026-10-13 | **reemplazada** por `3d02b991…` |
| landing | **Resumen, Cómo empezar y Planes — vigente v2** | Desktop 1440 / light | Estado **Anual** (Bs 350 al año, Bs 30 al mes), Ganancia en verde, anclas unificadas, pie mínimo | `10435969640252772563` | `567d596cb4624f0996d7d23d98c3557e` | — | 2026-10-13 | **revisado visualmente** (1440×2387); H6, P2, P3, P5 corregidas |
| landing | Resumen y Planes v1 | Desktop 1440 / light | Estado Mensual, pie con © 2024 y tagline | `10435969640252772563` | `e201288a509b48118a920a5b8392a872` | — | 2026-10-13 | **reemplazada** por `567d596c…` |
| landing | Hero y Entrega y pago (intento anterior) | Desktop 1440 / light | Generada por una llamada que expiró; no revisada | `10435969640252772563` | `52950247293945d1b7844a8aa1afd239` | — | 2026-10-13 | **sin revisar**; probablemente duplicado |
| landing | Secciones intermedias (intento anterior) | Desktop 1440 / light | Generada por una llamada que expiró; probablemente contiene "Qué puedes controlar"; no revisada | `10435969640252772563` | `28057be2e6ec406a890665be6b1d60f8` | — | 2026-10-13 | **sin revisar** |
| landing | Datos, FAQ, cierre y pie | Desktop 1440 / light | Tarjeta de datos, acordeón de 6 preguntas, CTA de cierre, pie mínimo | `10435969640252772563` | `a6164829d8bd4b3f91a39fb91cab6835` | — | 2026-10-13 | **revisado visualmente** (1440×1670); desviación F1 |
| landing | Página completa (versión anterior, panel en vez de teléfono) | Desktop 1440 / light | Superada por las 4 pantallas anteriores | `10435969640252772563` | `7d18407f17504b25ae3b6ee7e716f0e8` | — | 2026-10-12 | **reemplazada** (contiene "Gestión ágil…", "300 Harinas Especiales" inventados) |
| landing | Página completa (versión larga anterior) | Desktop 1440 / light | Superada | `10435969640252772563` | `8d17cc5f3d8b4c86b2db2bb80e6dfc7a` | — | 2026-10-12 | **reemplazada** |
| landing | **Qué puedes controlar (4 tarjetas)** | Desktop 1440 / light | 4 tarjetas con icono; textos exactos | `10435969640252772563` | `358c02dbf09e47e5a61ceeb7585611fb` | — | 2026-10-13 | **revisado visualmente** (1440×1152); sin desviaciones de contenido |
| landing | **Hero móvil** | Móvil 390 / light | Cabecera con CTA y menú, hero, teléfono con dashboard, nota de límites | `10435969640252772563` | `190b408d30a0496ca7cdb18c868c86c1` | — | 2026-10-13 | **revisado visualmente** (780×1768 = 390 @2x); ver M1–M3 |
| landing | **Qué puedes controlar y Entrega y pago (móvil)** | Móvil (columna ≈400 px en lienzo 1440) / light | 4 tarjetas apiladas y secuencia de 3 pasos; Entrega=Listo, Cobro=Pendiente | `10435969640252772563` | `1c04e67402cc43898e423e31cc7470e8` | — | 2026-10-13 | **revisado visualmente**; ver M4 |
| landing | **Planes y Resumen (móvil)** | Móvil (columna ≈400 px en lienzo 1440) / light | Anual seleccionado, Gratis y Pro (sin botón de compra), 3 tarjetas de resumen | `10435969640252772563` | `42795c5fcb174f878cd0c989a17b4b37` | — | 2026-10-13 | **revisado visualmente**; ver M4, M5 |
| landing | **Datos, FAQ, cierre y pie (móvil)** | Móvil (columna ≈400 px en lienzo 1440) / light | Tarjeta de datos, acordeón de 6 preguntas, CTA de cierre, pie mínimo | `10435969640252772563` | `4ce1f6643e3c408bad00fc474512c15b` | — | 2026-10-13 | **revisado visualmente**; ver M4 |

## Referencias reales del producto (aportadas por el usuario, 2026-10-13)
Capturas de la aplicación (no son salidas de Stitch) en `docs/design/exports/landing/referencias-producto/`: `dashboard-movil-396.png`, `nuevo-pedido-canal-de-venta.png`, `pedido-listo-entrega-pendiente.png`, `pedido-entregado-pagado.png`. Contienen datos de una instancia de desarrollo ("oleon", "Empresa por defecto", "Joe Doe"); recortar antes de publicar. La especificación de la landing se actualizó para usarlas; la referencia de Stitch **no** refleja ese cambio.

## Exportaciones
| Archivo | Origen | Nota |
|---|---|---|
| `docs/design/exports/design-system/componentes/componentes-light-desktop-thumbnail.png` | `thumbnailScreenshot` del proyecto (`get_project`) | PNG 319×512. Es miniatura, no exportación a escala completa; no permite medir colores ni textos pequeños. HTML y captura completa no se obtuvieron porque no hay screen ID. |

## Exportaciones de la landing (2026-10-13)
En `docs/design/exports/landing/`:
| Carpeta | Archivos | Origen |
|---|---|---|
| `hero-section-5e57d193/` | `hero-desktop-light.png` (1440×1179) | `screenshot` de la pantalla (parámetro de ancho `=w1440` añadido a la URL devuelta) |
| `entrega-pago-3149862f/` | `entrega-pago-desktop-light.png` (1440×1152) | ídem |
| `planes-resumen-e201288a/` | `planes-resumen-desktop-light.png` (1440×2356) | ídem |
| `secciones-finales-a6164829/` | `secciones-finales-desktop-light.png` (1440×1670) | ídem |
| `stitch-7d18407f/`, `stitch-8d17cc5f/` | capturas, miniaturas y `landing.html` de las versiones **reemplazadas** | conservadas como evidencia, no vigentes |
| `referencias-producto/` | 5 capturas reales de la app aportadas por el usuario | no son de Stitch |

El HTML de las versiones reemplazadas se descargó solo como datos; no se ejecutó. No se guardaron URLs temporales en este registro.

## Desviaciones de la referencia (landing, 2026-10-13)
Revisión visual sobre capturas a 1440 px, contra `specs/landing-pagina-principal.md` y `design-system.md`.

| # | Pantalla | Desviación | Gravedad | Acción |
|---|---|---|---|---|
| H1 | Hero | Etiqueta "Gestión simplificada para negocios independientes": texto de marketing no pedido | Media | Eliminar |
| H2 | Hero | "Sin tarjeta de crédito requerida" (prohibido por AC-L04: no confirmado) | **Alta** | Eliminar |
| H3 | Hero | El teléfono es una **recreación** de Stitch, no la captura real aportada; incluye elementos inventados: insignia "+3.8%", "Al día", "Local abierto", barra inferior Inicio/Pedidos/Cobros/Gastos, "Último movimiento · Panadería San José · Bs 120.00" | **Alta** | En implementación, usar `dashboard-movil-403-positivo.png` dentro del marco; en diseño, no tomar esos elementos como funcionalidad |
| H4 | Hero | Pestañas "Esta semana" / "Este mes" casi sin separación | Baja | Ajustar espaciado en la maqueta real |
| H5 | Hero y pantallas | Icono del logo (toldo de tienda) inventado; no es `main-logo.png`/`simple-logo.png` | Media | Usar el logo real |
| H6 | Hero y planes | Pie con "© 2024 PocketBiz…", "Privacidad", "Términos", "Contacto" y eslogan "Control operativo diario para pequeños negocios"; esos documentos no existen (Q4/Q6) y el año es incorrecto | **Alta** | Pie mínimo (wordmark + Iniciar sesión), como en `a6164829` |
| H7 | Hero | Cifras coinciden con la captura real (280.50 / 270.00 / 10.50 / 4) | — | Conforme |
| H8 | Hero | Nota "Plan gratuito con límites: 1 producto, 1 cliente, 2 ventas y 2 gastos por día." presente | — | Conforme |
| E1 | Entrega y pago | En el paso 2, "Listo" aparece bajo "Preparación" y "Pendiente" bajo "Entrega"; en el producto, "Listo" es el estado de **Entrega** y "Pendiente" es el estado de **Cobro** | **Alta** | Corregir: Entrega = Listo; Cobro = Pendiente + Saldo Bs 28.00 |
| P1 | Resumen | Subtítulos de tarjeta inventados ("Total ingresos registrados", "Salidas operativas registradas", "Diferencial calculado"); el producto dice "Total de los pedidos del periodo" | Media | Usar textos reales |
| P2 | Resumen | La tarjeta Ganancia estimada va en azul; en el producto, verde si ≥ 0 | Baja | Verde (`success-text`) |
| P3 | Planes | Estado Anual no mostrado (solo Mensual); no se ve Bs 350 al año | Media | Generar/espec. estado Anual |
| P4 | Resumen y planes | Textos de relleno: "Sin configuraciones complejas ni curvas lentas de aprendizaje", "Para validar tu registro diario sin costo", "Operativa completa para negocios con mayor ritmo" | Baja | Revisar o eliminar |
| P5 | Navegación | Las anclas del encabezado cambian entre pantallas (Tu resumen / Cómo empezar / Planes) | Media | Unificar: Qué puedes controlar · Cómo funciona · Planes · Preguntas |
| F1 | Datos | Icono de escudo con "Tus datos, tu empresa" sugiere seguridad certificada | Baja | Icono neutro (empresa/edificio) |
| F2 | Planes | Pro con mucho espacio vacío bajo la única viñeta | Baja | Ajuste de layout |

Texto de las pantallas: coincide con lo especificado (CTA, límites, Pro sin botón de compra con "Pago disponible próximamente", FAQ de 6 preguntas, pie mínimo en `a6164829`).

## Correcciones de desviaciones altas (2026-10-13)
`edit_screens` aceptó las 3 ediciones (devolvió operaciones DOM), pero los archivos descargables (captura y HTML, mismos nombres de archivo y hash) **no cambiaron**: no se pudo verificar ni entregar el resultado. Por eso se regeneraron las 3 pantallas con `generate_screen_from_text` y se revisaron visualmente.

| # | Estado | Evidencia |
|---|---|---|
| H1 insignia sobre el título | **Corregida** | Hero v2: sin insignia |
| H2 "Sin tarjeta de crédito requerida" | **Corregida** | Hero v2: solo la nota de límites |
| H3 elementos inventados en el teléfono | **Corregida** | Hero v2: sin barra inferior, "+3.8 %", "Al día", "Local abierto" ni "Último movimiento". Sigue siendo recreación, no la captura real (ver abajo) |
| H4 pestañas pegadas | **Corregida** | Hero v2 con separación adecuada |
| H6 pie con © 2024 y enlaces legales | **Corregida** | Hero v2 sin pie; Planes v2 con pie mínimo (wordmark + Iniciar sesión) |
| E1 Listo/Pendiente mal asignados | **Corregida** | Entrega y pago v2: Entrega=Listo, Cobro=Pendiente, "Saldo Bs 28.00" |
| P2 ganancia en azul | **Corregida** | Planes v2: verde |
| P3 estado Anual | **Corregida** | Planes v2: Anual seleccionado, "Bs 350 al año (Bs 30 al mes)" |
| P5 anclas distintas | **Corregida** | Planes v2 usa Qué puedes controlar · Cómo funciona · Planes · Preguntas |
| H5 icono de logo inventado | **Abierta** | Hero v2 usa un icono de casa; Planes v2, un toldo. Ninguno es el logo real |
| H3 (resto) captura real | **Abierta** | El teléfono sigue siendo una maqueta de Stitch; en implementación va `dashboard-movil-403-positivo.png` |
| P1 / P4 textos de relleno | **Abierta (media/baja)** | Planes v2 conserva "Salidas operativas registradas", "Sin configuraciones complejas…", "Para validar tu registro diario sin costo", "Operativa completa para negocios con mayor ritmo", "Visualiza las cifras clave de tu operativa diaria…"; la nota de ganancia aparece dos veces |
| Espacio vacío | **Abierta (baja)** | Entrega y pago v2 y Hero v2 con mucho margen superior/inferior |

## Observaciones de la versión móvil y de "Qué puedes controlar" (2026-10-13)
| # | Pantalla | Observación | Gravedad | Acción |
|---|---|---|---|---|
| M1 | Hero móvil | En el teléfono, "Esta semana" y "Este mes" se parten en dos líneas | Baja | Abreviar o permitir scroll horizontal de pestañas |
| M2 | Hero móvil | Campana y logo de toldo inventados (H5) | Media | Usar logo real; quitar campana |
| M3 | Hero móvil | Teléfono es recreación, no la captura | Media | Usar `dashboard-movil-403-positivo.png` |
| M4 | 3 pantallas móviles | Se generaron con tipo DESKTOP (ancho 2560): son una **columna de ≈400 px centrada en un lienzo de 1440**, no un viewport de 390. El contenido y el orden vertical sirven; el lienzo no | Media | Rehacerlas con viewport móvil si se quiere exportar a 390 px exactos |
| M5 | Móvil (planes) | "Tu resumen" va **después** de Planes (la spec: Resumen → Cómo empezar → Planes); "Cómo empezar en tres pasos" **no está** en ninguna pantalla móvil | Media | Regenerar con el orden de la spec e incluir los 3 pasos |
| M6 | Móvil (planes) | Falta el selector de periodo (Hoy / Esta semana / Este mes / Rango) en "Tu resumen" | Baja | Añadir |
| M7 | Móvil (intermedias) | Paso 1 muestra "Canal de venta: WhatsApp" como chip; correcto en contenido | — | Conforme |
| Q1 | Qué puedes controlar | Subtítulo "Pedidos, cobros, gastos, clientes y productos, en un solo lugar." (añadido en el prompt, no estaba en la spec) | Baja | Incorporado a la spec |
| Q2 | Qué puedes controlar | Mucho margen superior/inferior | Baja | Ajustar en implementación |

## Intentos y limitaciones
- 1.ª generación (prompt largo): **timeout**; se comprobó durante ≈6 min con `list_screens` y `get_project` sin resultado y se repitió una sola vez con un prompt más corto, como pide el protocolo.
- **Landing, desktop:** 2 llamadas a `generate_screen_from_text` (prompt largo y uno más corto) terminaron en timeout sin respuesta. `list_screens` devuelve `{}` en todas las consultas posteriores (≈2 h), por lo que no se puede confirmar si alguna llegó a crearse; puede haber 0, 1 o 2 pantallas de landing en el proyecto. `updateTime` del proyecto cambió (2026-10-13T01:43Z), sin que eso pruebe una pantalla. No se pudo inspeccionar visualmente. El prompt usado está resumido en la especificación; no se declara referencia visual.
- **Actualización 2026-10-13:** `list_screens` terminó devolviendo las pantallas antiguas (con ID); las nuevas llegaron con ID en la respuesta de `generate_screen_from_text`. Los intentos largos expiran (>~1.200 caracteres de prompt); los tramos cortos se completan. `list_screens` va retrasado respecto a las generaciones nuevas.
- **Tramos de la landing:** hero (1 llamada OK), "Entrega y pago" (1.ª llamada expiró; reintento OK; no se confirmó si la 1.ª dejó una pantalla duplicada), resumen+planes (OK), finales (OK).
- **Observación anterior del MCP (2026-10-12):** ni `generate_screen_from_text` ni `list_screens` devolvían un screen ID; ya no aplica.
- No se generó la variante **dark**: queda pendiente (una iteración enfocada, si se aprueba).
- No se generó variante móvil (390): corresponde a `delivery-ui-design`.
- Pantallas de la landing: aún no generadas (etapa `delivery-ui-design`).
