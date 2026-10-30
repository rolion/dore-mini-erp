import { Route } from '@angular/router';
import { unsavedChangesGuard } from '../../core/guard/unsaved-changes.guard';
import { PurchaseDetailComponent } from './pages/purchase-detail/purchase-detail.component';
import { PurchaseFormComponent } from './pages/purchase-form/purchase-form.component';
import { PurchaseListComponent } from './pages/purchase-list/purchase-list.component';
import { ReceptionDetailComponent } from './pages/reception-detail/reception-detail.component';
import { ReceptionFormComponent } from './pages/reception-form/reception-form.component';
import { SupplierDetailComponent } from './pages/supplier-detail/supplier-detail.component';
import { SupplierFormComponent } from './pages/supplier-form/supplier-form.component';
import { SupplierListComponent } from './pages/supplier-list/supplier-list.component';

/** Rutas bajo `purchases/suppliers`. */
export const SUPPLIERS_ROUTE: Route[] = [
  { path: '', component: SupplierListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: SupplierFormComponent },
  { path: ':id/edit', component: SupplierFormComponent },
  { path: ':id', component: SupplierDetailComponent },
];

/** Rutas bajo `purchases`. Se montan después de `purchases/suppliers` y `purchases/settings` (ver `app.routes.ts`). */
export const PURCHASES_ROUTE: Route[] = [
  { path: '', component: PurchaseListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: PurchaseFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id/edit', component: PurchaseFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id/receipts/new', component: ReceptionFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id/receipts/:receiptId', component: ReceptionDetailComponent },
  { path: ':id', component: PurchaseDetailComponent },
];
