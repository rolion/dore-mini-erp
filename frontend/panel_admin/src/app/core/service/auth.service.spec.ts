import { TestBed } from '@angular/core/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';

import {
  AuthService,
  INVALID_CREDENTIALS_MESSAGE,
  SERVER_ERROR_MESSAGE,
  TOO_MANY_ATTEMPTS_MESSAGE,
} from './auth.service';

const LOGIN_RESPONSE = {
  token: 'tok-123',
  user: { id: 7, username: 'ana', first_name: 'Ana', last_name: 'Pérez' },
};

describe('AuthService', () => {
  let service: AuthService;
  let http: HttpTestingController;

  beforeEach(() => {
    localStorage.clear();
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting()],
    });
    service = TestBed.inject(AuthService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => {
    http.verify();
    localStorage.clear();
  });

  it('should be created and start without session', () => {
    expect(service).toBeTruthy();
    expect(service.currentUserValue).toBeNull();
    expect(service.isAuthenticated).toBeFalse();
  });

  it('stores the session on successful login (AC-03)', () => {
    let result: unknown;
    service.login('ana', 'secret').subscribe((user) => (result = user));

    const req = http.expectOne('/api/auth/login/');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual({ username: 'ana', password: 'secret' });
    req.flush(LOGIN_RESPONSE);

    expect(result).toEqual({ id: 7, username: 'ana', firstName: 'Ana', lastName: 'Pérez', token: 'tok-123' });
    expect(service.isAuthenticated).toBeTrue();
    expect(service.currentUserValue?.token).toBe('tok-123');
  });

  it('rejects invalid credentials without storing a session (AC-04)', () => {
    let message = '';
    service.login('ana', 'mala').subscribe({ error: (e: Error) => (message = e.message) });
    http.expectOne('/api/auth/login/').flush({ detail: 'Credenciales inválidas.' }, { status: 401, statusText: 'Unauthorized' });

    expect(message).toBe(INVALID_CREDENTIALS_MESSAGE);
    expect(service.isAuthenticated).toBeFalse();
    expect(localStorage.length).toBe(0);
  });

  it('maps throttling and server errors to their own messages', () => {
    const messages: string[] = [];
    service.login('a', 'b').subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne('/api/auth/login/').flush({}, { status: 429, statusText: 'Too Many Requests' });
    service.login('a', 'b').subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne('/api/auth/login/').flush({}, { status: 500, statusText: 'Server Error' });
    service.login('a', 'b').subscribe({ error: (e: Error) => messages.push(e.message) });
    http.expectOne('/api/auth/login/').error(new ProgressEvent('error'));

    expect(messages).toEqual([TOO_MANY_ATTEMPTS_MESSAGE, SERVER_ERROR_MESSAGE, SERVER_ERROR_MESSAGE]);
  });

  it('restores the session from storage and ignores entries without token', () => {
    service.login('ana', 'secret').subscribe();
    http.expectOne('/api/auth/login/').flush(LOGIN_RESPONSE);
    expect(TestBed.runInInjectionContext(() => new AuthService()).isAuthenticated).toBeTrue();

    localStorage.setItem('light_currentUser', JSON.stringify({ id: 1, username: 'x' }));
    expect(TestBed.runInInjectionContext(() => new AuthService()).isAuthenticated).toBeFalse();
  });

  it('logout calls the API and clears the session (AC-06)', () => {
    service.login('ana', 'secret').subscribe();
    http.expectOne('/api/auth/login/').flush(LOGIN_RESPONSE);

    service.logout().subscribe();
    const req = http.expectOne('/api/auth/logout/');
    expect(req.request.method).toBe('POST');
    req.flush(null, { status: 204, statusText: 'No Content' });

    expect(service.isAuthenticated).toBeFalse();
    expect(localStorage.length).toBe(0);
  });

  it('logout clears the local session even if the API fails', () => {
    service.login('ana', 'secret').subscribe();
    http.expectOne('/api/auth/login/').flush(LOGIN_RESPONSE);

    service.logout().subscribe();
    http.expectOne('/api/auth/logout/').flush({}, { status: 500, statusText: 'Server Error' });

    expect(service.isAuthenticated).toBeFalse();
  });

  it('logout without session does not call the API', () => {
    let result: { success: boolean } | undefined;
    service.logout().subscribe((res) => (result = res));
    http.expectNone('/api/auth/logout/');
    expect(result).toEqual({ success: false });
    expect(service.isAuthenticated).toBeFalse();
  });
});
