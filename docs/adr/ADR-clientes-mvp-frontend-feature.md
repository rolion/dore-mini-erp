# ADR-clientes-mvp-frontend-feature: Feature `customers`, rutas y menú

**Estado:** Propuesto
**Task relacionado:** TASK-clientes-mvp
**Fecha:** 2026-10-08

## Contexto
`ADR-catalogo-productos-mvp-frontend-feature` fijó la convención: `src/app/features/<modulo>/{pages,components,services,models}`, servicio HTTP único y tipado, `FormBuilder` tipado, `takeUntilDestroyed`/`async`, rutas perezosas bajo `MainLayoutComponent` + `AuthGuard`, menú desde `assets/data/routes.json` con claves `MENUITEMS.*` en `en/es/de`, sin dependencias nuevas. Hoy `features/` contiene solo `products/`. El DDR de clientes define: entrada de menú directa "Cliente", lista, formulario con diálogo de duplicado, perfil con historial, y deja abiertos los estilos compartidos de acciones de tabla. `ddd.md:1050-1060` indica `features/customers/{pages/customer-list,pages/customer-detail,components,services,models}`.

## Decisión
- **Estructura:** `src/app/features/customers/` con `pages/{customer-list,customer-form,customer-detail}`, `services/customers-api.service.ts`, `models/customer.ts` (`Customer`, `CustomerInput`, `CustomerOrderSummary`, `Page<T>` propio) y `customers.routes.ts`. El servicio es el único que habla HTTP (`environment.apiUrl + '/customers/'`), devuelve `Observable` tipados y expone `create(input, confirmDuplicate = false)`.
- **Errores:** 400 `{campo: [mensajes]}` se mapea a un error tipado por campo (como `ProductApiError`); 409 con `code: 'duplicate_phone'` se mapea a un error tipado `DuplicateCustomerError` con las coincidencias; 404 y errores de red se informan con `toastr`. El formulario, ante `DuplicateCustomerError`, abre el diálogo `sweetalert2` del DDR y, si el usuario confirma, repite `create(input, true)`; si cancela, conserva los datos.
- **Rutas:** `app.routes.ts` agrega `customers` con carga perezosa de `customers.routes.ts`, con `''`, `new`, `:id/edit` y `:id` (en ese orden de declaración para que `new` no sea capturado por `:id`).
- **Menú:** una entrada nueva en `routes.json` (`path: "/customers"`, icono feather `users`, `class: ""`, sin submenú) y la clave `MENUITEMS.CUSTOMER.TEXT` en `en.json` ("Customer"), `es.json` ("Cliente") y `de.json` ("Kunde"). Se conserva Dashboard y Catálogo.
- **Historial:** la sección del perfil depende de `CustomerOrderSummary`, pero no hay servicio HTTP de pedidos todavía (ver `ADR-clientes-mvp-historial-compras`): se renderiza el estado vacío sin petición de red.
- **Reutilización sin acoplar features:** `features/customers` **no importa** nada de `features/products` (ni `Page<T>` ni sus componentes). Se acepta duplicar el tipo `Page<T>`; se extraerá a `shared/` cuando una tercera feature lo necesite. Los estilos de acciones de tabla (`btn-tbl-view/update/toggle`, hoy en el SCSS de `product-list`) se **copian al SCSS de `customer-list`** en este task y se registra la deuda; extraerlos a un estilo global es un cambio que toca `products` y se deja a un task aparte.
- **Sin nuevas dependencias npm.** Tests Karma: spec del servicio (`HttpTestingController`, incluido el 409), de lista, formulario (flujo de duplicado) y perfil, y ampliación de `layout/sidebar/sidebar-menu.spec.ts` para la entrada "Cliente". Se aplica la salvedad conocida de la suite completa (`app.component.spec.ts` no compila en `main`; specs de plantilla fallando): se verifican los specs de la feature.
- **Creación rápida desde pedido:** no se construye (no existe `features/sales`); cuando exista, el modal reutilizará `CustomersApiService.create` y el mismo diálogo de duplicado (que conviene extraer entonces a `components/` de la feature).

## Alternativas consideradas
- **Importar `Page<T>` y los estilos desde `features/products`:** menos código, pero crea acoplamiento entre features hermanas; descartado a favor de copia mínima con deuda explícita.
- **Refactorizar ahora `shared/` (modelos y estilos de tabla):** más limpio, pero modifica el feature de productos ya publicado y amplía el diff; descartado.
- **Grupo de menú "Cliente ▸ Clientes":** descartado en el DDR.
- **Diálogo de duplicado como componente propio:** hoy es un solo uso (`Swal`); se extrae cuando haya el segundo (modal de pedido).

## Estrategia de rollback / mitigación
Aditivo: una carpeta nueva, una ruta y una entrada de menú. Rollback = revertir el PR; el menú vuelve a su contenido anterior (en git). No afecta autenticación (reutiliza `AuthGuard` e interceptor) ni infraestructura.

## Consecuencias
- Queda fácil: la feature es autocontenida y replicable; el servicio se prueba aislado; conectar el historial y la creación rápida más adelante no obliga a rehacer pantallas.
- Queda más difícil: dos copias de estilos de acción y de `Page<T>` hasta que se extraigan.
- Deuda aceptada: pantallas solo en español (el menú sí usa `translate`); rutas de demo siguen accesibles por URL; sección de historial sin datos reales hasta Sales.
