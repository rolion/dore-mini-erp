import { Injectable, inject } from '@angular/core';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { BehaviorSubject, Observable, catchError, map, of, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { LoginResponse, User } from '../models/user';
import { LocalStorageService } from './storage.service';

export const INVALID_CREDENTIALS_MESSAGE = 'Credenciales inválidas';
export const SERVER_ERROR_MESSAGE = 'No se pudo conectar con el servidor. Inténtalo de nuevo.';
export const TOO_MANY_ATTEMPTS_MESSAGE = 'Demasiados intentos. Espera un momento e inténtalo de nuevo.';

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
        map((res): User => ({
          id: res.user.id,
          username: res.user.username,
          firstName: res.user.first_name,
          lastName: res.user.last_name,
          token: res.token,
        })),
        tap((user) => {
          this.storageService.set('currentUser', user);
          this.currentUserSubject.next(user);
        }),
        catchError((err: HttpErrorResponse) =>
          throwError(() => new Error(this.loginErrorMessage(err.status)))
        )
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
}
