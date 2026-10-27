import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { BehaviorSubject, Observable, catchError, finalize, map, of, share, tap, throwError } from 'rxjs';
import { environment } from '../../../environments/environment';
import { AppModule, BASE_MODULE_KEYS, ModuleDto, ModulesApiError, toAppModule } from '../models/module';

export const MODULES_ERROR_MESSAGE = 'No se pudieron cargar los módulos. Inténtalo de nuevo.';
const GENERIC_MESSAGE = 'Ocurrió un error inesperado. Inténtalo de nuevo.';

/** Estado de los módulos de la empresa del usuario: alimenta el menú, el guard y la pantalla de módulos. */
@Injectable({
  providedIn: 'root',
})
export class ModulesService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/modules/`;
  private readonly modulesSubject = new BehaviorSubject<AppModule[] | null>(null);
  private readonly enabledSubject = new BehaviorSubject<ReadonlySet<string> | null>(null);
  private inflight: Observable<AppModule[]> | null = null;

  /** `null` mientras no se cargó; con error de carga solo contiene los módulos base. */
  readonly enabledKeys$: Observable<ReadonlySet<string> | null> = this.enabledSubject.asObservable();
  readonly modules$: Observable<AppModule[] | null> = this.modulesSubject.asObservable();

  get enabledKeysValue(): ReadonlySet<string> | null {
    return this.enabledSubject.value;
  }

  /**
   * Consulta los módulos de la empresa; ante un error deja solo los base y re-emite el error. Las llamadas
   * simultáneas (guard y menú en una carga en frío) comparten una sola petición.
   */
  load(): Observable<AppModule[]> {
    if (!this.inflight) {
      this.inflight = this.request();
    }
    return this.inflight;
  }

  private request(): Observable<AppModule[]> {
    return this.http.get<ModuleDto[]>(this.baseUrl).pipe(
      map((dtos) => dtos.map(toAppModule)),
      tap((modules) => this.publish(modules)),
      catchError((err: HttpErrorResponse) => {
        this.modulesSubject.next(null);
        this.enabledSubject.next(new Set(BASE_MODULE_KEYS));
        return throwError(() => new ModulesApiError(MODULES_ERROR_MESSAGE, err.status));
      }),
      finalize(() => (this.inflight = null)),
      share(),
    );
  }

  /** Igual que `load` pero sin propagar el error: para el arranque del menú. */
  loadQuietly(): Observable<AppModule[] | null> {
    return this.load().pipe(catchError(() => of(null)));
  }

  enable(key: string): Observable<AppModule> {
    return this.change(key, 'enable');
  }

  disable(key: string): Observable<AppModule> {
    return this.change(key, 'disable');
  }

  /** Olvida el estado (cierre de sesión): la próxima sesión vuelve a consultar. */
  reset(): void {
    this.modulesSubject.next(null);
    this.enabledSubject.next(null);
  }

  private change(key: string, action: 'enable' | 'disable'): Observable<AppModule> {
    return this.http.post<ModuleDto>(`${this.baseUrl}${key}/${action}/`, {}).pipe(
      map(toAppModule),
      tap((changed) => this.applyChange(changed)),
      catchError((err: HttpErrorResponse) => throwError(() => this.toError(err))),
    );
  }

  private applyChange(changed: AppModule): void {
    const current = this.modulesSubject.value;
    if (current) {
      this.publish(current.map((m) => (m.key === changed.key ? changed : m)));
    }
  }

  private publish(modules: AppModule[]): void {
    this.modulesSubject.next(modules);
    this.enabledSubject.next(new Set(modules.filter((m) => m.enabled).map((m) => m.key)));
  }

  private toError(err: HttpErrorResponse): ModulesApiError {
    const body = (err.error && typeof err.error === 'object' ? err.error : {}) as {
      detail?: unknown;
      missing?: unknown;
      dependents?: unknown;
    };
    const detail = typeof body.detail === 'string' ? body.detail : '';
    const names = [body.missing, body.dependents].find(Array.isArray);
    return new ModulesApiError(
      err.status === 0 ? MODULES_ERROR_MESSAGE : detail || GENERIC_MESSAGE,
      err.status,
      names ? names.map(String) : [],
    );
  }
}
