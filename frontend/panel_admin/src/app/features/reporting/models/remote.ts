import { BehaviorSubject, Observable, catchError, map, of, shareReplay, startWith, switchMap } from 'rxjs';

/** Estado de una consulta que carga por su cuenta: cada tarjeta puede estar cargando, fallar o estar lista. */
export type Remote<T> =
  | { status: 'loading'; data: null; error: '' }
  | { status: 'ready'; data: T; error: '' }
  | { status: 'error'; data: null; error: string };

const LOADING: Remote<never> = { status: 'loading', data: null, error: '' };

export function toRemote<T>(source: Observable<T>): Observable<Remote<T>> {
  return source.pipe(
    map((data): Remote<T> => ({ status: 'ready', data, error: '' })),
    catchError((err: Error) => of<Remote<T>>({ status: 'error', data: null, error: err.message })),
    startWith<Remote<T>>(LOADING),
  );
}

/**
 * Consulta que se puede repetir: `reload()` vuelve a pedirla (cambio de periodo o "Reintentar") sin tocar
 * las demás tarjetas, y descarta la respuesta anterior si aún no llegó.
 */
export class RemoteResource<T> {
  readonly state$: Observable<Remote<T>>;
  private readonly reload$ = new BehaviorSubject<void>(undefined);

  constructor(fetch: () => Observable<T>) {
    // Compartido: varios `async` sobre el mismo estado no deben repetir la petición.
    this.state$ = this.reload$.pipe(
      switchMap(() => toRemote(fetch())),
      shareReplay({ bufferSize: 1, refCount: true }),
    );
  }

  reload(): void {
    this.reload$.next();
  }
}
