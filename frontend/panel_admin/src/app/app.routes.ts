import { Route } from '@angular/router';
import { MainLayoutComponent } from './layout/app-layout/main-layout/main-layout.component';
import { AuthGuard } from './core/guard/auth.guard';
import { AuthLayoutComponent } from './layout/app-layout/auth-layout/auth-layout.component';
import { moduleGuard } from './core/guard/module.guard';
import { unsavedChangesGuard } from './core/guard/unsaved-changes.guard';
import { Page404Component } from './authentication/page404/page404.component';
import { LEGACY_REDIRECTS } from './core/routing/legacy-redirects';

export const APP_ROUTE: Route[] = [
    // Landing pública (sin AuthGuard ni layout del panel), carga diferida.
    {
        path: '',
        pathMatch: 'full',
        loadComponent: () => import('./features/landing').then((m) => m.LandingComponent),
    },
    {
        path: 'pocketbiz',
        children: [
    // El grupo privado va primero: "/pocketbiz" (vacío) debe resolver a su redirect y no al layout
    // público vacío; "login", "signup", etc. no coinciden con sus hijas y caen al grupo público.
    {
        path: '',
        component: MainLayoutComponent,
        canActivate: [AuthGuard],
        children: [
            { path: '', redirectTo: 'dashboard/main', pathMatch: 'full' },
            {
                path: 'dashboard',
                canActivate: [moduleGuard],
                data: { module: 'reporting' },
                loadChildren: () =>
                    import('./dashboard/dashboard.routes').then((m) => m.DASHBOARD_ROUTE),
            },
            {
                path: 'catalog/products',
                canActivate: [moduleGuard],
                data: { module: 'catalog' },
                loadChildren: () =>
                    import('./features/products/products.routes').then((m) => m.PRODUCTS_ROUTE),
            },
            {
                path: 'customers',
                canActivate: [moduleGuard],
                data: { module: 'customers' },
                loadChildren: () =>
                    import('./features/customers/customers.routes').then((m) => m.CUSTOMERS_ROUTE),
            },
            {
                path: 'sales/orders',
                canActivate: [moduleGuard],
                data: { module: 'sales' },
                loadChildren: () =>
                    import('./features/sales/sales.routes').then((m) => m.SALES_ORDERS_ROUTE),
            },
            {
                path: 'sales/settings',
                canActivate: [moduleGuard],
                canDeactivate: [unsavedChangesGuard],
                data: { module: 'sales', settingsModule: 'sales' },
                loadComponent: () =>
                    import('./features/settings/pages/module-settings/module-settings.component').then(
                        (m) => m.ModuleSettingsComponent
                    ),
            },
            {
                path: 'expenses',
                canActivate: [moduleGuard],
                data: { module: 'expenses' },
                loadChildren: () =>
                    import('./features/expenses/expenses.routes').then((m) => m.EXPENSES_ROUTE),
            },
            {
                path: 'reports',
                canActivate: [moduleGuard],
                data: { module: 'reporting' },
                loadChildren: () =>
                    import('./features/reporting/reporting.routes').then((m) => m.REPORTS_ROUTE),
            },
            {
                path: 'purchases',
                canActivate: [moduleGuard],
                data: { module: 'purchases', title: 'Compras' },
                loadComponent: () =>
                    import('./features/settings/pages/coming-soon/coming-soon.component').then(
                        (m) => m.ComingSoonComponent
                    ),
            },
            {
                path: 'inventory',
                canActivate: [moduleGuard],
                data: { module: 'inventory', title: 'Inventario' },
                loadComponent: () =>
                    import('./features/settings/pages/coming-soon/coming-soon.component').then(
                        (m) => m.ComingSoonComponent
                    ),
            },
            {
                path: 'purchases/settings',
                canActivate: [moduleGuard],
                canDeactivate: [unsavedChangesGuard],
                data: { module: 'purchases', settingsModule: 'purchases' },
                loadComponent: () =>
                    import('./features/settings/pages/module-settings/module-settings.component').then(
                        (m) => m.ModuleSettingsComponent
                    ),
            },
            {
                path: 'inventory/stock',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/stock-list/stock-list.component').then(
                        (m) => m.StockListComponent
                    ),
            },
            {
                path: 'inventory/stock/:productId/:warehouseId',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/stock-detail/stock-detail.component').then(
                        (m) => m.StockDetailComponent
                    ),
            },
            {
                path: 'inventory/stock/opening',
                canActivate: [moduleGuard],
                canDeactivate: [unsavedChangesGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/stock-opening/stock-opening.component').then(
                        (m) => m.StockOpeningComponent
                    ),
            },
            {
                path: 'inventory/configuration',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/inventory-configuration/inventory-configuration.component').then(
                        (m) => m.InventoryConfigurationComponent
                    ),
            },
            {
                path: 'inventory/movements',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadChildren: () =>
                    import('./features/inventory/inventory.routes').then((m) => m.INVENTORY_MOVEMENTS_ROUTE),
            },
            {
                path: 'inventory/adjustments',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/adjustment-list/adjustment-list.component').then(
                        (m) => m.AdjustmentListComponent
                    ),
            },
            {
                path: 'inventory/adjustments/new',
                canActivate: [moduleGuard],
                canDeactivate: [unsavedChangesGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/adjustment-form/adjustment-form.component').then(
                        (m) => m.AdjustmentFormComponent
                    ),
            },
            {
                path: 'inventory/adjustments/:id',
                canActivate: [moduleGuard],
                data: { module: 'inventory' },
                loadComponent: () =>
                    import('./features/inventory/pages/adjustment-detail/adjustment-detail.component').then(
                        (m) => m.AdjustmentDetailComponent
                    ),
            },
            {
                path: 'inventory/settings',
                canActivate: [moduleGuard],
                canDeactivate: [unsavedChangesGuard],
                data: { module: 'inventory', settingsModule: 'inventory' },
                loadComponent: () =>
                    import('./features/settings/pages/module-settings/module-settings.component').then(
                        (m) => m.ModuleSettingsComponent
                    ),
            },
            {
                path: 'module-disabled',
                loadComponent: () =>
                    import('./features/settings/pages/module-disabled/module-disabled.component').then(
                        (m) => m.ModuleDisabledComponent
                    ),
            },
            {
                path: 'settings/modules',
                loadComponent: () =>
                    import('./features/settings/pages/module-list/module-list.component').then(
                        (m) => m.ModuleListComponent
                    ),
            },
            {
                path: 'advance-table',
                loadChildren: () =>
                    import('./advance-table/advance-table.routes').then(
                        (m) => m.ADVANCE_TABLE_ROUTE
                    ),
            },
            {
                path: 'advanced',
                loadChildren: () =>
                    import('./advanced-component/advanced-component.routes').then(
                        (m) => m.ADVANCE_COMPONENT_ROUTE
                    ),
            },
            {
                path: 'calendar',
                loadChildren: () =>
                    import('./calendar/calendar.routes').then((m) => m.CALENDAR_ROUTE),
            },
            {
                path: 'email',
                loadChildren: () =>
                    import('./email/email.routes').then((m) => m.EMAIL_ROUTE),
            },
            {
                path: 'apps',
                loadChildren: () =>
                    import('./apps/apps.routes').then((m) => m.APPS_ROUTE),
            },
            {
                path: 'widget',
                loadChildren: () =>
                    import('./widget/widget.routes').then((m) => m.WIDGET_ROUTE),
            },
            {
                path: 'ui',
                loadChildren: () => import('./ui/ui.routes').then((m) => m.UI_ROUTE),
            },
            {
                path: 'forms',
                loadChildren: () =>
                    import('./forms/forms.routes').then((m) => m.FORMS_ROUTE),
            },

            {
                path: 'charts',
                loadChildren: () =>
                    import('./charts/charts.routes').then((m) => m.CHART_ROUTE),
            },
            {
                path: 'icons',
                loadChildren: () =>
                    import('./icons/icons.routes').then((m) => m.ICONS_ROUTE),
            },
            {
                path: 'extra-pages',
                loadChildren: () =>
                    import('./extra-pages/extra-pages.routes').then(
                        (m) => m.EXTRA_PAGES_ROUTE
                    ),
            },
            {
                path: 'maps',
                loadChildren: () =>
                    import('./maps/maps.routes').then((m) => m.MAPS_ROUTE),
            },
            {
                path: 'multilevel',
                loadChildren: () =>
                    import('./multilevel/multilevel.routes').then(
                        (m) => m.MULTILEVEL_ROUTE
                    ),
            },
            {
                path: 'tables',
                loadChildren: () =>
                    import('./tables/tables.routes').then((m) => m.TABLES_ROUTE),
            },
            {
                path: 'data-tables',
                loadChildren: () =>
                    import('./data-tables/data-tables.routes').then(
                        (m) => m.DATATABLE_ROUTE
                    ),
            },
        ],
    },
    {
        path: '',
        component: AuthLayoutComponent,
        loadChildren: () =>
            import('./authentication/auth.routes').then((m) => m.AUTH_ROUTE),
    },
        ],
    },
    // Compatibilidad temporal con las URLs anteriores a /pocketbiz (ver ADR).
    ...LEGACY_REDIRECTS,
    { path: '**', component: Page404Component },
];
