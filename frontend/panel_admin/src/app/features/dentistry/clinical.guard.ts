import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of } from 'rxjs';
import { DentistryApiService } from './services/dentistry-api.service';

export const clinicalGuard: CanActivateFn = () => {
  const api = inject(DentistryApiService);
  const router = inject(Router);
  const denied = router.createUrlTree(['/pocketbiz/dentistry/access-denied']);
  return api.capabilities().pipe(map(result => result.clinical_access ? true : denied), catchError(() => of(denied)));
};
