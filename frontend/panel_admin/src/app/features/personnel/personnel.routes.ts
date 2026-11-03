import { inject } from '@angular/core';
import { CanActivateFn, Router, Routes } from '@angular/router';
import { AuthService } from '../../core/service/auth.service';
import { ProfileKind } from './models/profile';

// Es solo presentación. El servidor aplica empresa, admin y gate en cada petición.
export const personnelAdminGuard: CanActivateFn = () => inject(AuthService).currentUserValue?.role === 'admin'
  || inject(Router).createUrlTree(['/pocketbiz/dashboard/main']);

function pages(kind: ProfileKind): Routes {
  return [
    { path: kind, canActivate: [personnelAdminGuard], data: { kind }, loadComponent: () => import('./pages/profile-list.component').then(m => m.ProfileListComponent) },
    { path: `${kind}/new`, canActivate: [personnelAdminGuard], data: { kind }, loadComponent: () => import('./pages/profile-form.component').then(m => m.ProfileFormComponent) },
    { path: `${kind}/:id/edit`, canActivate: [personnelAdminGuard], data: { kind }, loadComponent: () => import('./pages/profile-form.component').then(m => m.ProfileFormComponent) },
    { path: `${kind}/:id`, canActivate: [personnelAdminGuard], data: { kind }, loadComponent: () => import('./pages/profile-detail.component').then(m => m.ProfileDetailComponent) },
  ];
}
export const PERSONNEL_ROUTES: Routes = [
  { path: '', redirectTo: 'professionals', pathMatch: 'full' }, ...pages('professionals'), ...pages('specialties'),
];
