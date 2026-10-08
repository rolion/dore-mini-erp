import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, UrlTree, provideRouter } from '@angular/router';

import { AuthService } from '../service/auth.service';
import { AuthGuard } from './auth.guard';

describe('AuthGuard', () => {
  let guard: AuthGuard;
  let auth: AuthService;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([])],
    });
    guard = TestBed.inject(AuthGuard);
    auth = TestBed.inject(AuthService);
  });

  afterEach(() => localStorage.clear());

  it('redirects to signin when there is no session (AC-05)', () => {
    const result = guard.canActivate();
    expect(result instanceof UrlTree).toBeTrue();
    expect(TestBed.inject(Router).serializeUrl(result as UrlTree)).toBe('/authentication/signin');
  });

  it('allows access when there is a token', () => {
    spyOnProperty(auth, 'isAuthenticated', 'get').and.returnValue(true);
    expect(guard.canActivate()).toBeTrue();
  });
});
