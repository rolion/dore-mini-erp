import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, map, of, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LoginResponse, RegisterField, RegisterInput, User } from '../models/user';
import { LocalStorageService } from './storage.service';

export const INVALID_CREDENTIALS_MESSAGE = 'Credenciales inválidas';
export const SERVER_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const TOO_MANY_ATTEMPTS_MESSAGE = 'Demasiados intentos. Espera un momento e inténtalo de nuevo.';
export const REGISTRATION_DISABLED_MESSAGE = 'El registro no está disponible por el momento.';
export const REGISTER_INVALID_MESSAGE = 'Revisa los datos marcados e inténtalo de nuevo.';

/** Campo del backend (snake_case) → control del formulario de registro. */
const REGISTER_FIELD_BY_API_KEY: Record<string, RegisterField> = {
  company_name: 'companyName',
  username: 'username',
  first_name: 'firstName',
  last_name: 'lastName',
  email: 'email',
  password: 'password',
};

/** Registro rechazado: `fieldErrors` trae el primer mensaje del servidor por campo del formulario. */
export class RegisterError extends Error {
  constructor(
    message: string,
    readonly fieldErrors: Partial<Record<RegisterField, string>> = {}
  ) {
    super(message);
    this.name = 'RegisterError';
  }
}

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private http = inject(HttpClient);
  private storageService = inject(LocalStorageService);
  private currentUserSubject = new BehaviorSubject<User | null>(this.readStoredUser());
  public currentUser: Observable<User | null> = this.currentUserSubject.asObservable();

  public get currentUserValue(): User | null {
    return this.currentUserSubject.value;
  }

  public get isAuthenticated(): boolean {
    return !!this.currentUserValue?.token;
  }

  login(username: string, password: string): Observable<User> {
    return this.http
      .post<LoginResponse>(`${environment.apiUrl}/auth/login/`, { username, password })
      .pipe(
        map((res) => this.toUser(res)),
        tap((user) => this.startSession(user)),
        catchError((err: HttpErrorResponse) =>
          throwError(() => new Error(this.loginErrorMessage(err.status)))
        )
      );
  }

  /** Crea la empresa y su primer usuario admin; deja la sesión iniciada igual que el login. */
  register(input: RegisterInput): Observable<User> {
    const body = {
      company_name: input.companyName,
      username: input.username,
      first_name: input.firstName,
      last_name: input.lastName,
      email: input.email,
      password: input.password,
    };
    return this.http.post<LoginResponse>(`${environment.apiUrl}/auth/register/`, body).pipe(
      map((res) => this.toUser(res)),
      tap((user) => this.startSession(user)),
      catchError((err: HttpErrorResponse) => throwError(() => this.registerError(err)))
    );
  }

  /** Cierra la sesión en el servidor (si hay token) y siempre limpia la sesión local. */
  logout(): Observable<{ success: boolean }> {
    const finish = (): { success: boolean } => {
      this.clearSession();
      return { success: false };
    };
    if (!this.isAuthenticated) {
      return of(finish());
    }
    return this.http.post(`${environment.apiUrl}/auth/logout/`, {}).pipe(
      map(finish),
      catchError(() => of(finish()))
    );
  }

  /** Limpia solo el estado local; no llama al backend. */
  clearSession(): void {
    this.storageService.remove('currentUser');
    this.currentUserSubject.next(null);
  }

  private toUser(res: LoginResponse): User {
    const user: User = {
      id: res.user.id,
      username: res.user.username,
      firstName: res.user.first_name,
      lastName: res.user.last_name,
      token: res.token,
    };
    if (res.user.role) {
      user.role = res.user.role;
    }
    if (res.user.company) {
      user.company = res.user.company;
    }
    return user;
  }

  private startSession(user: User): void {
    this.storageService.set('currentUser', user);
    this.currentUserSubject.next(user);
  }

  private readStoredUser(): User | null {
    const stored = this.storageService.get('currentUser') as Partial<User> | null;
    return stored && typeof stored.token === 'string' && stored.token ? (stored as User) : null;
  }

  private loginErrorMessage(status: number): string {
    switch (status) {
      case 401:
        return INVALID_CREDENTIALS_MESSAGE;
      case 429:
        return TOO_MANY_ATTEMPTS_MESSAGE;
      default:
        return SERVER_ERROR_MESSAGE;
    }
  }

  private registerError(err: HttpErrorResponse): RegisterError {
    switch (err.status) {
      case 400:
        return new RegisterError(REGISTER_INVALID_MESSAGE, this.fieldErrors(err.error));
      case 403:
        return new RegisterError(REGISTRATION_DISABLED_MESSAGE);
      case 429:
        return new RegisterError(TOO_MANY_ATTEMPTS_MESSAGE);
      default:
        return new RegisterError(SERVER_ERROR_MESSAGE);
    }
  }

  private fieldErrors(body: unknown): Partial<Record<RegisterField, string>> {
    const errors: Partial<Record<RegisterField, string>> = {};
    if (!body || typeof body !== 'object') {
      return errors;
    }
    for (const [key, value] of Object.entries(body as Record<string, unknown>)) {
      const field = REGISTER_FIELD_BY_API_KEY[key];
      const message = Array.isArray(value) ? value[0] : value;
      if (field && typeof message === 'string') {
        errors[field] = message;
      }
    }
    return errors;
  }
}
