import { Route } from '@angular/router';
import { RowDetailsComponent } from './row-details/row-details.component';
import { FilterComponent } from './filter/filter.component';
import { BasicDatatableComponent } from './basic-datatable/basic-datatable.component';
import { PinningComponent } from './pinning/pinning.component';

export const DATATABLE_ROUTE: Route[] = [
  {
    path: 'basic',
    component: BasicDatatableComponent,
  },
  {
    path: 'filter',
    component: FilterComponent,
  },
  {
    path: 'row-details',
    component: RowDetailsComponent,
  },
  {
    path: 'pinning',
    component: PinningComponent,
  },
];

