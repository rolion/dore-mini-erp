import { Route } from '@angular/router';
import { CustomerDetailComponent } from './pages/customer-detail/customer-detail.component';
import { CustomerFormComponent } from './pages/customer-form/customer-form.component';
import { CustomerListComponent } from './pages/customer-list/customer-list.component';

export const CUSTOMERS_ROUTE: Route[] = [
  { path: '', component: CustomerListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: CustomerFormComponent },
  { path: ':id/edit', component: CustomerFormComponent },
  { path: ':id', component: CustomerDetailComponent },
];
