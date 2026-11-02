import { Component } from '@angular/core';
import { Route, RouterLink } from '@angular/router';
import { unsavedChangesGuard } from '../../core/guard/unsaved-changes.guard';
import { clinicalGuard } from './clinical.guard';
import { PatientListComponent } from './pages/patient-list.component';
import { PatientCreateComponent } from './pages/patient-create.component';
import { PatientDetailComponent } from './pages/patient-detail.component';

@Component({
  selector: 'app-clinical-denied',
  imports: [RouterLink],
  template: `<section class="main-content"><div class="card"><div class="card-body">
    <h4>Acceso clínico no disponible</h4><p>No se pudo verificar el permiso para acceder a Odontología.</p>
    <a class="btn btn-primary" routerLink="/pocketbiz/dentistry/patients">Reintentar</a>
    <a class="btn btn-light ms-2" routerLink="/pocketbiz/dashboard/main">Volver al inicio</a>
    </div></div></section>`,
})
export class ClinicalDeniedComponent {}

export const DENTISTRY_ROUTES: Route[] = [
  { path: 'access-denied', component: ClinicalDeniedComponent },
  { path: 'patients', component: PatientListComponent, canActivate: [clinicalGuard] },
  { path: 'patients/new', component: PatientCreateComponent, canActivate: [clinicalGuard] },
  { path: 'patients/:id', component: PatientDetailComponent, canActivate: [clinicalGuard], canDeactivate: [unsavedChangesGuard] },
  { path: '', redirectTo: 'patients', pathMatch: 'full' },
];
