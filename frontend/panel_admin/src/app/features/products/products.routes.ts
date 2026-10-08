import { Route } from '@angular/router';
import { ProductDetailComponent } from './pages/product-detail/product-detail.component';
import { ProductFormComponent } from './pages/product-form/product-form.component';
import { ProductListComponent } from './pages/product-list/product-list.component';

export const PRODUCTS_ROUTE: Route[] = [
  { path: '', component: ProductListComponent },
  // `new` va antes que `:id` para que no se interprete como un id.
  { path: 'new', component: ProductFormComponent },
  { path: ':id/edit', component: ProductFormComponent },
  { path: ':id', component: ProductDetailComponent },
];
