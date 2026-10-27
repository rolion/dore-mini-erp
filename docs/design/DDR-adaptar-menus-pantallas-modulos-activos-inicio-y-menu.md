# DDR-adaptar-menus-pantallas-modulos-activos-inicio-y-menu: Inicio y menú según los módulos activos

**Estado:** Propuesto
**Task relacionado:** TASK-adaptar-menus-pantallas-modulos-activos
**Fecha:** 2026-10-27

## Contexto
PB-MOD-001 oculta ítems de primer nivel y PB-MOD-002 lleva a «Módulo no habilitado» al abrir un módulo apagado. Faltan los grupos del menú (hijos), una página inicial válida cuando Reportes está apagado y un mecanismo reutilizable para mostrar campos solo si su módulo está activo.

## Pantallas/flujos afectados
- Menú lateral: grupos Catálogo, Gastos y Configuración.
- Inicio: `/pocketbiz/dashboard/main`, login, registro, logo e iconos de inicio de las pantallas de negocio.
- Pantallas con controles opcionales de Clientes (lista y formulario de pedidos, Reportes).

## Componentes/patrones elegidos
- **Menú:** misma lista del sistema de diseño (§6). Un grupo se muestra solo si tiene al menos un hijo visible; los hijos heredan el módulo del grupo salvo que declaren el suyo en `routes.json`. Sin estilos nuevos.
- **Inicio:** sin pantalla nueva. Si Reportes está habilitado, el inicio es el dashboard; si no, la ruta del dashboard redirige sin mensaje a Catálogo (`/pocketbiz/catalog/products`), que es base. Así login, logo e iconos de inicio no cambian y nunca llevan a una pantalla de error.
- **Otras URLs de módulos deshabilitados:** siguen mostrando «Módulo no habilitado» (DDR de PB-MOD-002).
- **Campos por módulo:** directiva estructural `*appIfModule="'<clave>'"` en `shared/`; renderiza su contenido solo cuando el módulo está habilitado (y no mientras se cargan). Sustituye a los getters `customersDisabled` de las plantillas y queda lista para los campos de almacén y stock cuando exista Inventario.

## Alternativas consideradas
- Mostrar siempre «Módulo no habilitado» también para el inicio: el login con Reportes apagado aterrizaría en un error (descartada por el usuario).
- Resolver el inicio en cada icono con un enlace dinámico: toca ~13 plantillas; la redirección en el guard cubre todos los casos con un cambio.
- Crear campos de Inventario ficticios: se inventaría alcance (descartado).

## Comportamiento por privilegio/estado
- Estados: el menú se muestra con lo que se conoce; mientras los módulos no cargan solo hay ítems sin módulo; ante error de carga, solo los base (PB-MOD-001).
- El frontend no es la barrera: la API rechaza (403 `module_disabled`, PB-MOD-002).

## Consecuencias
La redirección silenciosa aplica solo a la ruta del dashboard; un marcador del dashboard con Reportes apagado lleva a Catálogo sin aviso. Se actualiza `design-system.md` §6.
