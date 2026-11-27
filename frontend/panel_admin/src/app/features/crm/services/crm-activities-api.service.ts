import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CrmActivity, CrmActivityDetails, CrmActivityDto, CrmActivityInput, CrmActivityPage, CrmActivityPageDto,
} from '../models/activity';
import { CrmRelated } from '../models/task';
import { crmErrors } from './crm-api-error';

export function toActivity(dto: CrmActivityDto): CrmActivity {
  return {
    id: dto.id,
    customerId: dto.customer_id,
    opportunityId: dto.opportunity_id,
    taskId: dto.task_id,
    actor: dto.actor,
    channel: dto.channel,
    outcome: dto.outcome,
    notes: dto.notes,
    occurredAt: dto.occurred_at,
    createdAt: dto.created_at,
  };
}

/** Cuerpo de una actividad sin el relacionado (también lo usa «Completar tarea»). */
export function activityBody(details: CrmActivityDetails): Record<string, string | null> {
  return {
    channel: details.channel,
    outcome: details.outcome || null,
    notes: details.notes.trim(),
    occurred_at: details.occurredAt ?? null,
  };
}

/** Relacionado → clave de la API: `customer_id` u `opportunity_id`. */
export function relatedKey(related: Pick<CrmRelated, 'type' | 'id'>): Record<string, string> {
  return related.type === 'customer' ? { customer_id: related.id } : { opportunity_id: related.id };
}

/** Actividad comercial (`/api/crm/activities/`). Solo se agrega y se consulta. */
@Injectable({ providedIn: 'root' })
export class CrmActivitiesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/activities/`;

  list(related: Pick<CrmRelated, 'type' | 'id'>, page = 1, pageSize = 20): Observable<CrmActivityPage> {
    const params = new HttpParams({ fromObject: { ...relatedKey(related), page: String(page), page_size: String(pageSize) } });
    return this.http.get<CrmActivityPageDto>(this.baseUrl, { params }).pipe(
      map((result): CrmActivityPage => ({ count: result.count, results: result.results.map(toActivity) })),
      crmErrors(),
    );
  }

  create(input: CrmActivityInput): Observable<CrmActivity> {
    return this.http.post<CrmActivityDto>(this.baseUrl, { ...relatedKey(input.related), ...activityBody(input) }).pipe(
      map(toActivity),
      crmErrors(),
    );
  }
}
