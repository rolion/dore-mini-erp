import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CrmLead, CrmLeadConversion, CrmLeadConversionDto, CrmLeadDto, CrmLeadInput, CrmLeadListParams, CrmLeadPage,
  CrmLeadPageDto,
} from '../models/lead';
import { crmErrors } from './crm-api-error';

export function toLead(dto: CrmLeadDto): CrmLead {
  return {
    id: dto.id,
    name: dto.name,
    phone: dto.phone ?? '',
    normalizedPhone: dto.normalized_phone ?? '',
    email: dto.email ?? '',
    convertedCustomerId: dto.converted_customer_id,
    createdAt: dto.created_at,
  };
}

/** Prospectos del CRM (`/api/crm/leads/`). Los errores llegan como `CrmApiError`. */
@Injectable({ providedIn: 'root' })
export class CrmLeadsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/leads/`;

  list(params: CrmLeadListParams = {}): Observable<CrmLeadPage> {
    let httpParams = new HttpParams();
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.converted !== undefined) httpParams = httpParams.set('converted', String(params.converted));
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<CrmLeadPageDto>(this.baseUrl, { params: httpParams }).pipe(
      map((page): CrmLeadPage => ({ count: page.count, results: page.results.map(toLead) })),
      crmErrors(),
    );
  }

  get(leadId: string): Observable<CrmLead> {
    return this.http.get<CrmLeadDto>(`${this.baseUrl}${leadId}/`).pipe(map(toLead), crmErrors());
  }

  create(input: CrmLeadInput): Observable<CrmLead> {
    return this.http.post<CrmLeadDto>(this.baseUrl, input).pipe(map(toLead), crmErrors());
  }

  update(leadId: string, input: Partial<CrmLeadInput>): Observable<CrmLead> {
    return this.http.patch<CrmLeadDto>(`${this.baseUrl}${leadId}/`, input).pipe(map(toLead), crmErrors());
  }

  /** Convierte en cliente (idempotente). Sin `customerId` el servidor busca por teléfono o crea el cliente. */
  convert(leadId: string, customerId?: string): Observable<CrmLeadConversion> {
    const body = customerId ? { customer_id: customerId } : {};
    return this.http.post<CrmLeadConversionDto>(`${this.baseUrl}${leadId}/convert/`, body).pipe(
      map((dto): CrmLeadConversion => ({ lead: toLead(dto.lead), customer: dto.customer, created: dto.created })),
      crmErrors(),
    );
  }
}
