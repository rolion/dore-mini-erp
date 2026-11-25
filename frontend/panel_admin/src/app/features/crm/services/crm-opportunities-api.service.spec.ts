import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { CrmApiError } from '../models/board';
import { CrmLinkableOrder, CrmOpportunityDto, CrmOpportunityPage, CrmStageChange } from '../models/opportunity';
import { CrmOpportunitiesApiService } from './crm-opportunities-api.service';

describe('CrmOpportunitiesApiService', () => {
  let api: CrmOpportunitiesApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/opportunities/`;
  const dto: CrmOpportunityDto = {
    id: 'o-1', board_id: 'b-1', stage_id: 's-1', lead: { id: 'l-1', name: 'Carla', phone: '7' }, customer: null,
    title: 'Combo', owner: { id: 7, name: 'Ana' }, amount: '150.00', currency: 'BOB', next_action_at: '2026-11-25T14:00:00Z',
    status: 'open', closed_at: null, order_id: null, lost_reason: '', created_at: '2026-11-20T10:00:00Z',
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmOpportunitiesApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists by board with every filter and maps to the model (API-03)', () => {
    let page: CrmOpportunityPage | undefined;
    api.list({ boardId: 'b-1', ownerId: 7, leadId: 'l-1', customerId: 'c-1', status: 'won', page: 1, pageSize: 200 })
      .subscribe((p) => (page = p));
    const req = http.expectOne((r) => r.url === base);
    const params = req.request.params;
    expect(['board_id', 'owner_id', 'lead_id', 'customer_id', 'status', 'page', 'page_size'].map((k) => params.get(k)))
      .toEqual(['b-1', '7', 'l-1', 'c-1', 'won', '1', '200']);
    req.flush({ count: 1, next: null, previous: null, results: [dto] });
    expect(page?.results[0]).toEqual(jasmine.objectContaining({
      id: 'o-1', boardId: 'b-1', stageId: 's-1', owner: { id: 7, name: 'Ana' }, amount: '150.00',
      nextActionAt: '2026-11-25T14:00:00Z', status: 'open', orderId: null,
    }));
  });

  it('sends only the board when no filter is set', () => {
    api.list({ boardId: 'b-1' }).subscribe();
    const req = http.expectOne((r) => r.url === base);
    expect(req.request.params.keys()).toEqual(['board_id']);
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('sends each write to its endpoint with the expected body (API-03, API-04)', () => {
    const cases: [() => void, string, string, unknown][] = [
      [() => api.create({ boardId: 'b-1', leadId: 'l-1', title: 'T', amount: '10.00' }).subscribe(), 'POST', base,
        { board_id: 'b-1', title: 'T', amount: '10.00', lead_id: 'l-1' }],
      [() => api.create({ boardId: 'b-1', stageId: 's-2', customerId: 'c-1', title: 'T', amount: '0', nextActionAt: '2026-11-25T14:00:00.000Z', ownerId: 9 }).subscribe(),
        'POST', base, { board_id: 'b-1', title: 'T', amount: '0', stage_id: 's-2', customer_id: 'c-1', next_action_at: '2026-11-25T14:00:00.000Z', owner_id: 9 }],
      [() => api.update('o-1', { title: 'N', amount: '5.50', nextActionAt: null, ownerId: 3 }).subscribe(), 'PATCH', `${base}o-1/`,
        { title: 'N', amount: '5.50', next_action_at: null, owner_id: 3 }],
      [() => api.move('o-1', 's-2').subscribe(), 'POST', `${base}o-1/move/`, { stage_id: 's-2' }],
      [() => api.close('o-1', { result: 'lost', lostReason: 'Precio' }).subscribe(), 'POST', `${base}o-1/close/`, { result: 'lost', lost_reason: 'Precio' }],
      [() => api.close('o-1', { result: 'won' }).subscribe(), 'POST', `${base}o-1/close/`, { result: 'won' }],
      [() => api.close('o-1', { result: 'won', orderId: 'p-1' }).subscribe(), 'POST', `${base}o-1/close/`, { result: 'won', order_id: 'p-1' }],
      [() => api.setOrder('o-1', 'p-1').subscribe(), 'PUT', `${base}o-1/order/`, { order_id: 'p-1' }],
    ];
    for (const [call, method, url, body] of cases) {
      call();
      const req = http.expectOne(url);
      expect(req.request.method).toBe(method);
      expect(req.request.body).toEqual(body);
      req.flush(dto);
    }
  });

  it('reads linkable orders and stage history (API-04)', () => {
    let orders: CrmLinkableOrder[] = [];
    let history: CrmStageChange[] = [];
    api.linkableOrders('o-1').subscribe((o) => (orders = o));
    http.expectOne(`${base}o-1/orders/`).flush([{ id: 'p-1', order_date: '2026-11-21', total: '150.00', status: 'DELIVERED' }]);
    api.history('o-1').subscribe((h) => (history = h));
    http.expectOne(`${base}o-1/history/`).flush([{ from_stage_id: null, to_stage_id: 's-1', changed_by: 7, changed_at: '2026-11-20T10:00:00Z' }]);
    expect(orders).toEqual([{ id: 'p-1', orderDate: '2026-11-21', total: '150.00', status: 'DELIVERED' }]);
    expect(history).toEqual([{ fromStageId: null, toStageId: 's-1', changedBy: 7, changedAt: '2026-11-20T10:00:00Z' }]);
  });

  it('translates 400 field errors to camelCase, 409 codes and network failures', () => {
    const errors: CrmApiError[] = [];
    api.close('o-1', { result: 'lost', lostReason: '' }).subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(`${base}o-1/close/`).flush({ lost_reason: ['Indica el motivo.'] }, { status: 400, statusText: 'Bad Request' });
    api.move('o-1', 's-9').subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(`${base}o-1/move/`).flush({ detail: 'Ya está cerrada.', code: 'opportunity_closed' }, { status: 409, statusText: 'Conflict' });
    api.list({ boardId: 'b-1' }).subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne((r) => r.url === base).error(new ProgressEvent('error'));
    expect(errors[0].fieldErrors['lostReason']).toBe('Indica el motivo.');
    expect([errors[1].status, errors[1].code, errors[1].message]).toEqual([409, 'opportunity_closed', 'Ya está cerrada.']);
    expect(errors[2].status).toBe(0);
    expect(errors[2].message).toBe('No se pudo conectar con el servidor.');
  });
});
