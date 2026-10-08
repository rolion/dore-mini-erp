import { Route } from '@angular/router';
import { AdvanceTableComponent } from './advance-table/advance-table.component';
import { BasicTableComponent } from './basic-table/basic-table.component';

export const TABLES_ROUTE: Route[] = [
  {
    path: 'basic-tables',
    component: BasicTableComponent,
  },
  {
    path: 'advance-tables',
    component: AdvanceTableComponent,
  },
];

