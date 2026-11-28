import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, map } from 'rxjs';
import { environment } from '../../../../environments/environment';
import {
  InboxConversation, InboxConversationDto, InboxListParams, InboxMessage, InboxMessageDto, InboxNewOpportunity,
  InboxPage, InboxTemplate,
} from '../models/inbox';
import { CrmOpportunity, CrmOpportunityDto } from '../models/opportunity';
import { crmErrors } from './crm-api-error';
import { toOpportunity } from './crm-opportunities-api.service';

export function toInboxConversation(dto: InboxConversationDto): InboxConversation {
  return {
    id: dto.id,
    phone: dto.phone,
    contact: dto.contact,
    owner: dto.owner,
    opportunity: dto.opportunity,
    lastMessage: dto.last_message,
    windowOpen: dto.window_open,
    windowExpiresAt: dto.window_expires_at,
    connectionActive: dto.connection_active ?? null,
  };
}

export function toInboxMessage(dto: InboxMessageDto): InboxMessage {
  const text = dto.type === 'text'
    ? String(dto.content['body'] ?? '')
    : dto.type === 'template' ? String(dto.content['name'] ?? '') : `[${dto.type}]`;
  return {
    id: dto.id,
    direction: dto.direction,
    type: dto.type,
    text,
    status: dto.status,
    failureReason: dto.failure_reason,
    createdAt: dto.created_at,
  };
}

/** Bandeja de WhatsApp (`/api/crm/inbox/`). Los errores llegan como `CrmApiError`. */
@Injectable({ providedIn: 'root' })
export class CrmInboxApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/inbox/conversations/`;

  list(params: InboxListParams = {}): Observable<InboxPage> {
    let httpParams = new HttpParams();
    if (params.scope) httpParams = httpParams.set('scope', params.scope);
    if (params.search) httpParams = httpParams.set('search', params.search);
    if (params.opportunityId) httpParams = httpParams.set('opportunity_id', params.opportunityId);
    if (params.page !== undefined) httpParams = httpParams.set('page', String(params.page));
    if (params.pageSize !== undefined) httpParams = httpParams.set('page_size', String(params.pageSize));
    return this.http.get<{ count: number; results: InboxConversationDto[] }>(this.baseUrl, { params: httpParams }).pipe(
      map((page): InboxPage => ({ count: page.count, results: page.results.map(toInboxConversation) })),
      crmErrors(),
    );
  }

  get(conversationId: string): Observable<InboxConversation> {
    return this.http.get<InboxConversationDto>(`${this.baseUrl}${conversationId}/`).pipe(map(toInboxConversation), crmErrors());
  }

  /** Con `after` (ISO) solo trae los mensajes creados desde esa fecha (incluida). */
  messages(conversationId: string, after?: string): Observable<InboxMessage[]> {
    const params = after ? new HttpParams().set('after', after) : new HttpParams();
    return this.http.get<{ results: InboxMessageDto[] }>(`${this.baseUrl}${conversationId}/messages/`, { params }).pipe(
      map((body) => body.results.map(toInboxMessage)),
      crmErrors(),
    );
  }

  sendText(conversationId: string, body: string): Observable<InboxMessage> {
    return this.http.post<InboxMessageDto>(`${this.baseUrl}${conversationId}/messages/`, { type: 'text', body }).pipe(
      map(toInboxMessage), crmErrors());
  }

  sendTemplate(conversationId: string, templateId: string): Observable<InboxMessage> {
    return this.http.post<InboxMessageDto>(`${this.baseUrl}${conversationId}/messages/`,
      { type: 'template', template_id: templateId }).pipe(map(toInboxMessage), crmErrors());
  }

  retry(conversationId: string, messageId: string): Observable<InboxMessage> {
    return this.http.post<InboxMessageDto>(`${this.baseUrl}${conversationId}/messages/${messageId}/retry/`, {}).pipe(
      map(toInboxMessage), crmErrors());
  }

  assign(conversationId: string, ownerId: number | null): Observable<InboxConversation> {
    return this.http.put<InboxConversationDto>(`${this.baseUrl}${conversationId}/owner/`, { owner_id: ownerId }).pipe(
      map(toInboxConversation), crmErrors());
  }

  /** Cliente, prospecto o ninguno (`null` quita el contacto). */
  setContact(conversationId: string, contact: { type: 'customer' | 'lead'; id: string } | null): Observable<InboxConversation> {
    const body = contact ? (contact.type === 'customer' ? { customer_id: contact.id } : { lead_id: contact.id }) : {};
    return this.http.put<InboxConversationDto>(`${this.baseUrl}${conversationId}/contact/`, body).pipe(
      map(toInboxConversation), crmErrors());
  }

  setOpportunity(conversationId: string, opportunityId: string | null): Observable<InboxConversation> {
    return this.http.put<InboxConversationDto>(`${this.baseUrl}${conversationId}/opportunity/`,
      { opportunity_id: opportunityId }).pipe(map(toInboxConversation), crmErrors());
  }

  createOpportunity(conversationId: string, input: InboxNewOpportunity): Observable<InboxConversation> {
    const body = { board_id: input.boardId, title: input.title.trim(), amount: input.amount };
    return this.http.post<InboxConversationDto>(`${this.baseUrl}${conversationId}/opportunity/`, body).pipe(
      map(toInboxConversation), crmErrors());
  }

  /** Oportunidades abiertas del contacto de la conversación. */
  linkableOpportunities(conversationId: string): Observable<CrmOpportunity[]> {
    return this.http.get<{ results: CrmOpportunityDto[] }>(`${this.baseUrl}${conversationId}/opportunities/`).pipe(
      map((body) => body.results.map(toOpportunity)),
      crmErrors(),
    );
  }

  /** Plantillas aprobadas (las sincroniza Configuración → WhatsApp). */
  approvedTemplates(): Observable<InboxTemplate[]> {
    return this.http.get<{ results: { id: string; name: string; language: string; status: string }[] }>(
      `${environment.apiUrl}/messaging/whatsapp/templates/`).pipe(
      map((body) => body.results.filter((t) => t.status === 'APPROVED').map((t) => ({ id: t.id, name: t.name, language: t.language }))),
      crmErrors(),
    );
  }
}
