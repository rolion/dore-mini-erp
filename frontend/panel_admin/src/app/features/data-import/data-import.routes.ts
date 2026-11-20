import { Route } from '@angular/router';
import { ImportDetailComponent } from './pages/import-detail/import-detail.component';
import { ImportHistoryComponent } from './pages/import-history/import-history.component';
import { SalesImportComponent } from './pages/sales-import/sales-import.component';

// Montadas en `/pocketbiz/sales/import` (con moduleGuard `sales`); el servidor exige rol admin.
export const DATA_IMPORT_ROUTE: Route[] = [
  { path: '', component: SalesImportComponent },
  { path: 'history', component: ImportHistoryComponent },
  { path: 'history/:id', component: ImportDetailComponent },
];
