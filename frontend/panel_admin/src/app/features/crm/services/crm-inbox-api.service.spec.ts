import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { CrmApiError } from '../models/board';
import { InboxConversationDto, InboxMessageDto } from '../models/inbox';
import { CrmInboxApiService } from './crm-inbox-api.service';

describe('CrmInboxApiService', () => {
  let api: CrmInboxApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/inbox/conversations/`;
  const dto: InboxConversationDto = {
    id: 'v-1', phone: '59176543210', contact: { type: 'customer', id: 'c-1', name: 'Ana' }, owner: { id: 7, name: 'Ana Admin' },
    opportunity: null, last_message: { type: 'text', preview: 'hola', direction: 'in', status: 'delivered', at: '2026-11-28T10:00:00Z' },
    window_open: true, window_expires_at: '2026-11-29T10:00:00Z', connection_active: true,
  };
  const messageDto: InboxMessageDto = {
    id: 'm-1', direction: 'out', type: 'text', content: { body: 'Hola Ana' }, status: 'failed', failure_reason: '400 inválido',
    created_at: '2026-11-28T10:01:00Z', sent_at: null,
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmInboxApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists with filters and maps the page (API-01)', () => {
    let first = '';
    let windowOpen = false;
    api.list({ scope: 'mine', search: 'ana', opportunityId: 'o-1', page: 2, pageSize: 20 }).subscribe((p) => {
      first = p.results[0].contact?.name ?? '';
      windowOpen = p.results[0].windowOpen;
    });
    const req = http.expectOne((r) => r.url === base);
    expect(req.request.params.get('scope')).toBe('mine');
    expect(req.request.params.get('search')).toBe('ana');
    expect(req.request.params.get('opportunity_id')).toBe('o-1');
    expect(req.request.params.get('page_size')).toBe('20');
    req.flush({ count: 1, next: null, previous: null, results: [dto] });
    expect([first, windowOpen]).toEqual(['Ana', true]);
  });

  it('reads the detail with the connection state (API-02)', () => {
    let active: boolean | null = null;
    api.get('v-1').subscribe((c) => (active = c.connectionActive));
    http.expectOne(`${base}v-1/`).flush(dto);
    expect(active as boolean | null).toBeTrue();
  });

  it('maps messages to the text to show and passes `after` (API-03)', () => {
    let texts: string[] = [];
    api.messages('v-1', '2026-11-28T10:00:00Z').subscribe((rows) => (texts = rows.map((m) => m.text)));
    const req = http.expectOne((r) => r.url === `${base}v-1/messages/`);
    expect(req.request.params.get('after')).toBe('2026-11-28T10:00:00Z');
    req.flush({ results: [messageDto, { ...messageDto, id: 'm-2', type: 'image', content: {} },
      { ...messageDto, id: 'm-3', type: 'template', content: { name: 'hola_mundo' } }] });
    expect(texts).toEqual(['Hola Ana', '[image]', 'hola_mundo']);
  });

  it('sends text and template messages (API-04)', () => {
    api.sendText('v-1', 'Hola').subscribe();
    expect(http.expectOne(`${base}v-1/messages/`).request.body).toEqual({ type: 'text', body: 'Hola' });
    api.sendTemplate('v-1', 't-1').subscribe();
    expect(http.expectOne(`${base}v-1/messages/`).request.body).toEqual({ type: 'template', template_id: 't-1' });
  });

  it('retries a failed message (API-05)', () => {
    api.retry('v-1', 'm-1').subscribe();
    const req = http.expectOne(`${base}v-1/messages/m-1/retry/`);
    expect(req.request.method).toBe('POST');
    req.flush({ ...messageDto, status: 'queued' });
  });

  it('assigns, links contact and opportunity (API-06..08)', () => {
    api.assign('v-1', 7).subscribe();
    const owner = http.expectOne(`${base}v-1/owner/`);
    expect([owner.request.method, owner.request.body]).toEqual(['PUT', { owner_id: 7 }]);
    owner.flush(dto);
    api.setContact('v-1', { type: 'lead', id: 'l-1' }).subscribe();
    expect(http.expectOne(`${base}v-1/contact/`).request.body).toEqual({ lead_id: 'l-1' });
    api.setContact('v-1', { type: 'customer', id: 'c-1' }).subscribe();
    expect(http.expectOne(`${base}v-1/contact/`).request.body).toEqual({ customer_id: 'c-1' });
    api.setContact('v-1', null).subscribe();
    expect(http.expectOne(`${base}v-1/contact/`).request.body).toEqual({});
    api.setOpportunity('v-1', null).subscribe();
    expect(http.expectOne(`${base}v-1/opportunity/`).request.body).toEqual({ opportunity_id: null });
    api.createOpportunity('v-1', { boardId: 'b-1', title: ' Pack ', amount: '10.00' }).subscribe();
    const created = http.expectOne(`${base}v-1/opportunity/`);
    expect([created.request.method, created.request.body]).toEqual(['POST', { board_id: 'b-1', title: 'Pack', amount: '10.00' }]);
  });

  it('keeps only approved templates', () => {
    let names: string[] = [];
    api.approvedTemplates().subscribe((rows) => (names = rows.map((t) => t.name)));
    http.expectOne(`${environment.apiUrl}/messaging/whatsapp/templates/`).flush({
      results: [{ id: 't-1', name: 'a', language: 'es', status: 'APPROVED' }, { id: 't-2', name: 'b', language: 'es', status: 'REJECTED' }],
    });
    expect(names).toEqual(['a']);
  });

  it('turns a 409 into a CrmApiError with its code', () => {
    let error: CrmApiError | null = null;
    api.sendText('v-1', 'Hola').subscribe({ error: (e: CrmApiError) => (error = e) });
    http.expectOne(`${base}v-1/messages/`).flush({ detail: 'La ventana de 24 h está cerrada', code: 'window_closed' },
      { status: 409, statusText: 'Conflict' });
    expect(error as CrmApiError | null).toEqual(jasmine.objectContaining({ status: 409, code: 'window_closed' }));
  });
});
