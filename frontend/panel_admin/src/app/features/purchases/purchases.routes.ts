import { Route } from '@angular/router';
import { SupplierDetailComponent } from './pages/supplier-detail/supplier-detail.component';
import { SupplierFormComponent } from './pages/supplier-form/supplier-form.component';
import { SupplierListComponent } from './pages/supplier-list/supplier-list.component';

/** Rutas bajo `purchases/suppliers` (la ruta `purchases` sigue siendo «Próximamente»). */
export const SUPPLIERS_ROUTE: Route[] = [
  { path: '', component: SupplierListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: SupplierFormComponent },
  { path: ':id/edit', component: SupplierFormComponent },
  { path: ':id', component: SupplierDetailComponent },
];
