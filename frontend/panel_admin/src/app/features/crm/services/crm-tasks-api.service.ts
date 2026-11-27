import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { CrmActivity, CrmActivityDetails, CrmActivityDto } from '../models/activity';
import {
  CrmTask, CrmTaskDto, CrmTaskInput, CrmTaskListParams, CrmTaskPage, CrmTaskPageDto, CrmTaskUpdate,
} from '../models/task';
import { activityBody, relatedKey, toActivity } from './crm-activities-api.service';
import { crmErrors } from './crm-api-error';

export function toTask(dto: CrmTaskDto): CrmTask {
  return {
    id: dto.id,
    title: dto.title,
    related: dto.related,
    owner: dto.owner,
    dueAt: dto.due_at,
    status: dto.status,
    isOverdue: dto.is_overdue,
    completedAt: dto.completed_at,
    createdAt: dto.created_at,
  };
}

/** Resultado de completar: la tarea y la actividad creada en el mismo paso (si se pidió). */
export interface CrmTaskCompletion {
  task: CrmTask;
  activity: CrmActivity | null;
}

/** Tareas comerciales (`/api/crm/tasks/`). Los errores llegan como `CrmApiError`. */
@Injectable({ providedIn: 'root' })
export class CrmTasksApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/tasks/`;

  list(params: CrmTaskListParams = {}): Observable<CrmTaskPage> {
    let httpParams = new HttpParams();
    if (params.ownerId !== undefined) httpParams = httpParams.set('owner_id', String(params.ownerId));
    if (params.status) httpParams = httpParams.set('status', params.status);
    if (params.customerId) httpParams = httpParams.set('customer_id', params.customerId);
    if (params.opportunityId) httpParams = httpParams.set('opportunity_id', params.opportunityId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<CrmTaskPageDto>(this.baseUrl, { params: httpParams }).pipe(
      map((page): CrmTaskPage => ({ count: page.count, results: page.results.map(toTask) })),
      crmErrors(),
    );
  }

  create(input: CrmTaskInput): Observable<CrmTask> {
    const body: Record<string, string | number> = { title: input.title.trim(), due_at: input.dueAt, ...relatedKey(input.related) };
    if (input.ownerId !== undefined) body['owner_id'] = input.ownerId;
    return this.http.post<CrmTaskDto>(this.baseUrl, body).pipe(map(toTask), crmErrors());
  }

  update(taskId: string, changes: CrmTaskUpdate): Observable<CrmTask> {
    const body: Record<string, string | number> = {};
    if (changes.title !== undefined) body['title'] = changes.title.trim();
    if (changes.dueAt !== undefined) body['due_at'] = changes.dueAt;
    if (changes.ownerId !== undefined) body['owner_id'] = changes.ownerId;
    return this.http.patch<CrmTaskDto>(`${this.baseUrl}${taskId}/`, body).pipe(map(toTask), crmErrors());
  }

  /** Completa; con `activity` registra además lo ocurrido en la misma operación. */
  complete(taskId: string, activity?: CrmActivityDetails): Observable<CrmTaskCompletion> {
    const body = activity ? { activity: activityBody(activity) } : {};
    return this.http.post<CrmTaskDto & { activity: CrmActivityDto | null }>(`${this.baseUrl}${taskId}/complete/`, body).pipe(
      map((dto): CrmTaskCompletion => ({ task: toTask(dto), activity: dto.activity ? toActivity(dto.activity) : null })),
      crmErrors(),
    );
  }

  cancel(taskId: string): Observable<CrmTask> {
    return this.action(taskId, 'cancel');
  }

  reopen(taskId: string): Observable<CrmTask> {
    return this.action(taskId, 'reopen');
  }

  archive(taskId: string): Observable<CrmTask> {
    return this.action(taskId, 'archive');
  }

  private action(taskId: string, action: string): Observable<CrmTask> {
    return this.http.post<CrmTaskDto>(`${this.baseUrl}${taskId}/${action}/`, {}).pipe(map(toTask), crmErrors());
  }
}
