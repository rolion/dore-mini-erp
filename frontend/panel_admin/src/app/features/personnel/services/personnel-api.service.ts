import { tr } from '../../../core/i18n/translate';
import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, expand, map, reduce, EMPTY } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { Page } from '../../../shared/models/page';
import { Profile, ProfileInput, ProfileKind, UserOption } from '../models/profile';

export function profileError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return tr('PERSONNEL.PERSONNEL_API_SERVICE.NO_SE_PUDO_COMPLETAR_LA');
  if (error.status === 403) return tr('PERSONNEL.PERSONNEL_API_SERVICE.NO_TIENES_PERMISO_O_PERSONAL');
  if (error.status === 404) return tr('PERSONNEL.PERSONNEL_API_SERVICE.REGISTRO_NO_ENCONTRADO');
  if (error.status === 400) return tr('PERSONNEL.PERSONNEL_API_SERVICE.REVISA_LOS_DATOS_MARCADOS');
  return tr('CUSTOMERS.CUSTOMERS_API_SERVICE.NO_SE_PUDO_CONECTAR_CON');
}

@Injectable({ providedIn: 'root' })
export class PersonnelApiService {
  private http = inject(HttpClient);
  private url(kind: ProfileKind): string { return `${environment.apiUrl}/${kind}/`; }

  list(kind: ProfileKind, params: Record<string, string | number | boolean> = {}): Observable<Page<Profile>> {
    return this.http.get<Page<Profile>>(this.url(kind), { params });
  }
  get(kind: ProfileKind, id: string): Observable<Profile> {
    return this.http.get<Profile>(`${this.url(kind)}${id}/`);
  }
  save(kind: ProfileKind, input: ProfileInput, id: string | null): Observable<Profile> {
    return id ? this.http.patch<Profile>(`${this.url(kind)}${id}/`, input)
      : this.http.post<Profile>(this.url(kind), input);
  }
  setActive(kind: ProfileKind, item: Profile): Observable<Profile> {
    return this.http.post<Profile>(`${this.url(kind)}${item.id}/${item.active ? 'deactivate' : 'activate'}/`, {});
  }
  specialties(): Observable<Profile[]> {
    let page = 1;
    return this.list('specialties', { page, page_size: 100 }).pipe(
      expand(result => result.next ? this.list('specialties', { page: ++page, page_size: 100 }) : EMPTY),
      map(result => result.results), reduce((all, rows) => [...all, ...rows], [] as Profile[]),
    );
  }
  users(search = '', id?: number): Observable<UserOption[]> {
    let params = new HttpParams().set('search', search).set('page_size', 100);
    if (id !== undefined) params = params.set('id', id);
    return this.http.get<Page<UserOption>>(`${this.url('professionals')}users/`, { params }).pipe(map(page => page.results));
  }
}
