import { TestBed } from '@angular/core/testing';
import { HttpClient, provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Router, provideRouter } from '@angular/router';

import { AuthService } from '../service/auth.service';
import { errorInterceptor } from './error.interceptor';
import { tokenInterceptor } from './jwt.interceptor';

describe('HTTP interceptors', () => {
  let http: HttpClient;
  let ctrl: HttpTestingController;
  let auth: AuthService;
  let router: Router;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([tokenInterceptor, errorInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
      ],
    });
    http = TestBed.inject(HttpClient);
    ctrl = TestBed.inject(HttpTestingController);
    auth = TestBed.inject(AuthService);
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
  });

  afterEach(() => {
    ctrl.verify();
    localStorage.clear();
  });

  function logIn() {
    auth.login('ana', 'x').subscribe();
    ctrl.expectOne('/api/auth/login/').flush({
      token: 'tok-1',
      user: { id: 1, username: 'ana', first_name: '', last_name: '' },
    });
  }

  it('sends the Token header to the API when there is a session (AC-07)', () => {
    logIn();
    http.get('/api/health/').subscribe();
    expect(ctrl.expectOne('/api/health/').request.headers.get('Authorization')).toBe('Token tok-1');
  });

  it('does not send the token without session nor to other origins', () => {
    http.get('/api/health/').subscribe();
    expect(ctrl.expectOne('/api/health/').request.headers.has('Authorization')).toBeFalse();
    logIn();
    http.get('https://example.com/x').subscribe();
    expect(ctrl.expectOne('https://example.com/x').request.headers.has('Authorization')).toBeFalse();
  });

  it('a 401 from the login does not clear nor redirect (EDGE-02)', () => {
    auth.login('ana', 'mala').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/auth/login/').flush({}, { status: 401, statusText: 'Unauthorized' });
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('a 401 elsewhere clears the session and goes to signin (EDGE-03)', () => {
    logIn();
    http.get('/api/ventas/').subscribe({ error: () => undefined });
    ctrl.expectOne('/api/ventas/').flush(null, { status: 401, statusText: 'Unauthorized' });
    expect(auth.isAuthenticated).toBeFalse();
    expect(router.navigate).toHaveBeenCalledWith(['/authentication/signin']);
  });
});
