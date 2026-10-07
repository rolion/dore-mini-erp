import { Injectable, inject } from '@angular/core';
import { Router, UrlTree } from '@angular/router';

import { AuthService } from '../service/auth.service';

@Injectable({
  providedIn: 'root',
})
export class AuthGuard {
  private authService = inject(AuthService);
  private router = inject(Router);

  canActivate(): boolean | UrlTree {
    if (this.authService.isAuthenticated) {
      return true;
    }
    return this.router.createUrlTree(['/authentication/signin']);
  }
}
