import { Route } from '@angular/router';
import { MovementDetailComponent } from './pages/movement-detail/movement-detail.component';
import { MovementListComponent } from './pages/movement-list/movement-list.component';

/** Movimientos de inventario: solo lectura, sin rutas de alta ni edición. */
export const INVENTORY_MOVEMENTS_ROUTE: Route[] = [
  { path: '', component: MovementListComponent },
  { path: ':id', component: MovementDetailComponent },
];
