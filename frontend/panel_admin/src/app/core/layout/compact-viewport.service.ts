import { DestroyRef, Injectable, inject, signal } from '@angular/core';

/** Ancho máximo (Bootstrap `lg`, 992 px) bajo el cual las listas pasan de tabla a tarjetas. */
export const COMPACT_VIEWPORT_QUERY = '(max-width: 991.98px)';

/**
 * Indica si la pantalla es estrecha. Existe para decidir en la plantilla (`@if`) qué vista renderizar sin dejar
 * `ngx-datatable` oculto con CSS: una tabla en `display: none` calcula mal su ancho al volver a mostrarse.
 */
@Injectable({ providedIn: 'root' })
export class CompactViewportService {
  private readonly query = typeof window !== 'undefined' && window.matchMedia ? window.matchMedia(COMPACT_VIEWPORT_QUERY) : null;
  private readonly state = signal(this.query?.matches ?? false);
  readonly compact = this.state.asReadonly();

  constructor() {
    if (!this.query) return;
    const onChange = (event: MediaQueryListEvent): void => this.state.set(event.matches);
    this.query.addEventListener('change', onChange);
    inject(DestroyRef).onDestroy(() => this.query?.removeEventListener('change', onChange));
  }
}
