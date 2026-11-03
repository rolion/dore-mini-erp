import { EMPTY, Observable, expand, reduce } from 'rxjs';
import { Page } from '../../../shared/models/page';

/** Recorre todas las páginas de un listado para no omitir registros sin aviso. */
export function fetchAll<T>(load: (page: number) => Observable<Page<T>>): Observable<T[]> {
  let page = 1;
  return load(page).pipe(
    expand(result => result.next ? load(++page) : EMPTY),
    reduce((all, result) => [...all, ...result.results], [] as T[]),
  );
}
