import { Route } from '@angular/router';
import { OrderDetailComponent } from './pages/order-detail/order-detail.component';
import { OrderFormComponent } from './pages/order-form/order-form.component';
import { OrderListComponent } from './pages/order-list/order-list.component';

export const SALES_ORDERS_ROUTE: Route[] = [
  { path: '', component: OrderListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: OrderFormComponent },
  { path: ':id/edit', component: OrderFormComponent },
  { path: ':id', component: OrderDetailComponent },
];
