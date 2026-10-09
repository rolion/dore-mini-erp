import { Route } from '@angular/router';
import { CategoryListComponent } from './pages/category-list/category-list.component';
import { ExpenseDetailComponent } from './pages/expense-detail/expense-detail.component';
import { ExpenseFormComponent } from './pages/expense-form/expense-form.component';
import { ExpenseListComponent } from './pages/expense-list/expense-list.component';

export const EXPENSES_ROUTE: Route[] = [
  { path: '', component: ExpenseListComponent },
  // `new` y `categories` van antes que `:id` para que no se interpreten como un id.
  { path: 'new', component: ExpenseFormComponent },
  { path: 'categories', component: CategoryListComponent },
  { path: ':id/edit', component: ExpenseFormComponent },
  { path: ':id', component: ExpenseDetailComponent },
];
