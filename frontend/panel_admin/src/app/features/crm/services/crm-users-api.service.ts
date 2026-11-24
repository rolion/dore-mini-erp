import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { CrmOwner } from '../models/opportunity';
import { crmErrors } from './crm-api-error';

/** Usuarios de la empresa para elegir responsable (`/api/crm/users/`). Los errores llegan como `CrmApiError`. */
@Injectable({ providedIn: 'root' })
export class CrmUsersApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/users/`;

  list(search = ''): Observable<CrmOwner[]> {
    let params = new HttpParams();
    if (search.trim()) params = params.set('search', search.trim());
    return this.http.get<CrmOwner[]>(this.baseUrl, { params }).pipe(crmErrors());
  }
}
