/** Página de resultados que devuelve la paginación de servidor (DRF). */
export interface Page<T> {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
}
