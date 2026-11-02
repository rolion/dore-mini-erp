import { Routes } from '@angular/router';
import { unsavedChangesGuard } from '../../core/guard/unsaved-changes.guard';
import { ServiceListComponent } from './pages/service-list.component';
import { ServiceFormComponent } from './pages/service-form.component';
import { ServiceDetailComponent } from './pages/service-detail.component';

export const SERVICES_ROUTE: Routes = [
  { path: '', component: ServiceListComponent },
  { path: 'new', component: ServiceFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id/edit', component: ServiceFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id', component: ServiceDetailComponent },
];
