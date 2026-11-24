import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  CrmCloseInput, CrmLinkableOrder, CrmLinkableOrderDto, CrmOpportunity, CrmOpportunityCreate, CrmOpportunityDto,
  CrmOpportunityFilters, CrmOpportunityPage, CrmOpportunityPageDto, CrmOpportunityUpdate, CrmStageChange,
  CrmStageChangeDto,
} from '../models/opportunity';
import { crmErrors } from './crm-api-error';

export function toOpportunity(dto: CrmOpportunityDto): CrmOpportunity {
  return {
    id: dto.id,
    boardId: dto.board_id,
    stageId: dto.stage_id,
    lead: dto.lead,
    customer: dto.customer,
    title: dto.title,
    owner: dto.owner,
    amount: dto.amount,
    currency: dto.currency,
    nextActionAt: dto.next_action_at,
    status: dto.status,
    closedAt: dto.closed_at,
    orderId: dto.order_id,
    lostReason: dto.lost_reason ?? '',
    createdAt: dto.created_at,
  };
}

/** Oportunidades del CRM (`/api/crm/opportunities/`). Los errores llegan como `CrmApiError`. */
@Injectable({ providedIn: 'root' })
export class CrmOpportunitiesApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/opportunities/`;

  list(filters: CrmOpportunityFilters): Observable<CrmOpportunityPage> {
    let params = new HttpParams().set('board_id', filters.boardId);
    if (filters.ownerId !== undefined) params = params.set('owner_id', String(filters.ownerId));
    if (filters.leadId) params = params.set('lead_id', filters.leadId);
    if (filters.customerId) params = params.set('customer_id', filters.customerId);
    if (filters.status) params = params.set('status', filters.status);
    if (filters.page !== undefined) params = params.set('page', String(filters.page));
    if (filters.pageSize !== undefined) params = params.set('page_size', String(filters.pageSize));
    return this.http.get<CrmOpportunityPageDto>(this.baseUrl, { params }).pipe(
      map((page): CrmOpportunityPage => ({ count: page.count, results: page.results.map(toOpportunity) })),
      crmErrors(),
    );
  }

  get(opportunityId: string): Observable<CrmOpportunity> {
    return this.one(this.http.get<CrmOpportunityDto>(this.url(opportunityId)));
  }

  create(input: CrmOpportunityCreate): Observable<CrmOpportunity> {
    const body: Record<string, string | number | null> = {
      board_id: input.boardId, title: input.title, amount: input.amount,
    };
    if (input.stageId) body['stage_id'] = input.stageId;
    if (input.leadId) body['lead_id'] = input.leadId;
    if (input.customerId) body['customer_id'] = input.customerId;
    if (input.nextActionAt) body['next_action_at'] = input.nextActionAt;
    if (input.ownerId !== undefined) body['owner_id'] = input.ownerId;
    return this.one(this.http.post<CrmOpportunityDto>(this.baseUrl, body));
  }

  /** Edita una oportunidad abierta; solo envía los campos indicados. */
  update(opportunityId: string, changes: CrmOpportunityUpdate): Observable<CrmOpportunity> {
    const body: Record<string, string | number | null> = {};
    if (changes.title !== undefined) body['title'] = changes.title;
    if (changes.amount !== undefined) body['amount'] = changes.amount;
    if (changes.nextActionAt !== undefined) body['next_action_at'] = changes.nextActionAt;
    if (changes.ownerId !== undefined) body['owner_id'] = changes.ownerId;
    return this.one(this.http.patch<CrmOpportunityDto>(this.url(opportunityId), body));
  }

  move(opportunityId: string, stageId: string): Observable<CrmOpportunity> {
    return this.one(this.http.post<CrmOpportunityDto>(`${this.url(opportunityId)}move/`, { stage_id: stageId }));
  }

  close(opportunityId: string, input: CrmCloseInput): Observable<CrmOpportunity> {
    const body: Record<string, string> = { result: input.result };
    if (input.result === 'lost' && input.lostReason !== undefined) body['lost_reason'] = input.lostReason;
    if (input.result === 'won' && input.orderId) body['order_id'] = input.orderId;
    return this.one(this.http.post<CrmOpportunityDto>(`${this.url(opportunityId)}close/`, body));
  }

  /** Vincula un pedido a una oportunidad ya ganada. */
  setOrder(opportunityId: string, orderId: string): Observable<CrmOpportunity> {
    return this.one(this.http.put<CrmOpportunityDto>(`${this.url(opportunityId)}order/`, { order_id: orderId }));
  }

  /** Pedidos del cliente de la oportunidad que se pueden vincular (no cancelados ni usados por otra). */
  linkableOrders(opportunityId: string): Observable<CrmLinkableOrder[]> {
    return this.http.get<CrmLinkableOrderDto[]>(`${this.url(opportunityId)}orders/`).pipe(
      map((orders) => orders.map((o): CrmLinkableOrder => ({
        id: o.id, orderDate: o.order_date, total: o.total, status: o.status,
      }))),
      crmErrors(),
    );
  }

  history(opportunityId: string): Observable<CrmStageChange[]> {
    return this.http.get<CrmStageChangeDto[]>(`${this.url(opportunityId)}history/`).pipe(
      map((changes) => changes.map((c): CrmStageChange => ({
        fromStageId: c.from_stage_id, toStageId: c.to_stage_id, changedBy: c.changed_by, changedAt: c.changed_at,
      }))),
      crmErrors(),
    );
  }

  private url(opportunityId: string): string {
    return `${this.baseUrl}${opportunityId}/`;
  }

  private one(request: Observable<CrmOpportunityDto>): Observable<CrmOpportunity> {
    return request.pipe(map(toOpportunity), crmErrors());
  }
}
