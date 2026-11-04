import { TranslatePipe } from '@ngx-translate/core';
import { Component, inject } from '@angular/core';
import { Route, Router, RouterLink } from '@angular/router';
import { unsavedChangesGuard } from '../../core/guard/unsaved-changes.guard';
import { clinicalGuard } from './clinical.guard';
import { PatientListComponent } from './pages/patient-list.component';
import { PatientDetailComponent } from './pages/patient-detail.component';
import { DentalProformaDetailComponent } from './pages/dental-proforma-detail.component';
import { DentalProformaFormComponent } from './pages/dental-proforma-form.component';

@Component({
  selector: 'app-clinical-denied',
  imports: [TranslatePipe, RouterLink],
  template: `<section class="main-content"><div class="card"><div class="card-body">
    <h4>{{ 'DENTISTRY.ROUTES.CLINICAL_ACCESS_UNAVAILABLE' | translate }}</h4><p>{{ 'DENTISTRY.ROUTES.PERMISSION_CHECK_FAILED' | translate }}</p>
    <a class="btn btn-primary" routerLink="/pocketbiz/dentistry/patients">{{ 'COMMON.REINTENTAR' | translate }}</a>
    <a class="btn btn-light ms-2" routerLink="/pocketbiz/dashboard/main">{{ 'COMMON.BACK_TO_HOME' | translate }}</a>
    </div></div></section>`,
})
export class ClinicalDeniedComponent {}

export const DENTISTRY_ROUTES: Route[] = [
  { path: 'access-denied', component: ClinicalDeniedComponent },
  { path: 'patients', component: PatientListComponent, canActivate: [clinicalGuard] },
  { path: 'patients/new', pathMatch: 'full', redirectTo: () => inject(Router).createUrlTree(['/pocketbiz/dentistry/patients'], { queryParams: { new: 'true' } }) },
  { path: 'patients/:id', component: PatientDetailComponent, canActivate: [clinicalGuard], canDeactivate: [unsavedChangesGuard] },
  { path: 'patients/:patientId/proformas/nueva', component: DentalProformaFormComponent, canActivate: [clinicalGuard], canDeactivate: [unsavedChangesGuard] },
  { path: 'proformas/:proformaId', component: DentalProformaDetailComponent, canActivate: [clinicalGuard] },
  { path: 'proformas/:proformaId/editar', component: DentalProformaFormComponent, canActivate: [clinicalGuard], canDeactivate: [unsavedChangesGuard] },
  { path: '', redirectTo: 'patients', pathMatch: 'full' },
];
