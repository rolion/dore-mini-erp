# ADR-catalogo-productos-mvp-frontend-feature: Feature `products`, rutas y menú

**Estado:** Propuesto
**Task relacionado:** TASK-catalogo-productos-mvp
**Fecha:** 2026-10-08

## Contexto
No existe `frontend/panel_admin/src/app/features/`; `CLAUDE.md` y `ddd.md:1035-1046` piden `features/<modulo>/{pages,components,services,models}` con servicio inyectable, tipos explícitos (sin `any`), Reactive Forms y sin suscripciones colgadas. El menú viene de `assets/data/routes.json` (`layout/sidebar/sidebar.service.ts:20-21`), las rutas de `app.routes.ts` cargan perezosamente bajo `MainLayoutComponent` + `AuthGuard`, y `jwt.interceptor.ts` ya agrega el token a `/api`. El DDR define lista, formulario (alta/edición) y detalle como páginas, y el menú con Dashboard + Catálogo ▸ Producto. Los componentes de demo de la plantilla usan `Untyped*` y datos locales.

## Decisión
- **Estructura:** `src/app/features/products/` con `pages/{product-list,product-form,product-detail}`, `services/products-api.service.ts`, `models/product.ts` (interfaces `Product`, `ProductInput`, `Page<T>`) y `products.routes.ts`. El servicio es el único que habla HTTP (`environment.apiUrl + '/products/'`) y devuelve `Observable` tipados; los componentes usan `FormBuilder` tipado y `takeUntilDestroyed`/`async` para evitar suscripciones colgadas.
- **Rutas:** en `app.routes.ts` se agrega `catalog` (carga perezosa de `products.routes.ts`) bajo el layout y guard existentes, con `products`, `products/new`, `products/:id` y `products/:id/edit`; `new` se declara antes que `:id`.
- **Errores de servidor:** el servicio expone el cuerpo 400 `{campo: [mensajes]}` para que el formulario lo muestre bajo cada campo; 404 y errores de red se informan con `toastr`.
- **Menú:** `routes.json` pasa a dos entradas (Dashboard → `/dashboard/main` sin submenú; Catálogo `menu-toggle` ▸ Producto → `/catalog/products`) y se agregan las claves `MENUITEMS.*` en `en.json`, `es.json`, `de.json`.
- **Rutas de demo:** **se retiran solo del menú**; las rutas y componentes de demo permanecen en `app.routes.ts` por ahora. Purgar la plantilla es un task aparte (borrar ~15 secciones y sus dependencias es un cambio amplio, independiente del Catálogo).
- **Sin nuevas dependencias npm** (se reutilizan `@swimlane/ngx-datatable`, `ngx-toastr`, `sweetalert2`, `@angular/forms`). Tests con Karma: spec del servicio (`HttpTestingController`) y de los componentes principales.

## Alternativas consideradas
- **Componentes en `src/app/products/` al estilo de las carpetas de la plantilla:** consistente con lo demo, pero contradice `CLAUDE.md`; `features/` es la convención del proyecto.
- **Reutilizar y modificar `advance-table`:** acorta el inicio pero arrastra formularios no tipados, datos locales y modales; se toma solo como referencia visual.
- **Borrar ahora las rutas y componentes de demo:** deja la app limpia pero amplía mucho el diff y el riesgo (imports cruzados, specs); se difiere.
- **`NgModule` o estado global (NgRx):** innecesario para tres pantallas.

## Estrategia de rollback / mitigación
Aditivo en frontend: una carpeta nueva, una ruta nueva y un cambio de `routes.json`/i18n. Rollback = revertir el PR; el menú vuelve a su contenido anterior, que sigue en el historial de git. No afecta autenticación (se reutiliza `AuthGuard` e interceptor) ni infraestructura.

## Consecuencias
- Queda fácil: replicar `features/<modulo>` para Customers/Sales/Expenses; probar el servicio de forma aislada.
- Queda más difícil: coexisten páginas de demo no enlazadas y una feature con convenciones estrictas hasta que se purgue la plantilla.
- Deuda aceptada: rutas de demo alcanzables por URL; contenido de Catálogo solo en español (el menú sí usa `translate`).
