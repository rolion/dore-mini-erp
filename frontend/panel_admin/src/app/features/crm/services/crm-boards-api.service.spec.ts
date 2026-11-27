import { provideTestTranslations } from '../../../core/i18n/testing';
import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { environment } from '../../../../environments/environment';
import { CrmApiError, CrmBoardDto } from '../models/board';
import { CrmBoardsApiService } from './crm-boards-api.service';

describe('CrmBoardsApiService', () => {
  let api: CrmBoardsApiService;
  let http: HttpTestingController;
  const base = `${environment.apiUrl}/crm/boards/`;
  const dto: CrmBoardDto = {
    id: 'b-1', name: 'Ventas', is_active: true,
    stages: [{ id: 's-1', name: 'Nuevo', position: 1, is_active: true, card_count: 2 }],
  };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    api = TestBed.inject(CrmBoardsApiService);
    http = TestBed.inject(HttpTestingController);
  });
  afterEach(() => http.verify());

  it('lists boards mapping snake_case to the model', () => {
    let result: unknown;
    api.list().subscribe((boards) => (result = boards));
    http.expectOne(base).flush([dto]);
    expect(result).toEqual([{ id: 'b-1', name: 'Ventas', isActive: true,
      stages: [{ id: 's-1', name: 'Nuevo', position: 1, isActive: true, cardCount: 2 }] }]);
  });

  it('sends each operation to its endpoint with the expected body', () => {
    const cases: [() => void, string, string, unknown][] = [
      [() => api.create('X').subscribe(), 'POST', base, { name: 'X' }],
      [() => api.rename('b-1', 'Y').subscribe(), 'PATCH', `${base}b-1/`, { name: 'Y' }],
      [() => api.archive('b-1').subscribe(), 'POST', `${base}b-1/archive/`, {}],
      [() => api.reactivate('b-1').subscribe(), 'POST', `${base}b-1/reactivate/`, {}],
      [() => api.addStage('b-1', 'E').subscribe(), 'POST', `${base}b-1/stages/`, { name: 'E' }],
      [() => api.renameStage('b-1', 's-1', 'F').subscribe(), 'PATCH', `${base}b-1/stages/s-1/`, { name: 'F' }],
      [() => api.reorderStages('b-1', ['s-2', 's-1']).subscribe(), 'PUT', `${base}b-1/stages/order/`, { stage_ids: ['s-2', 's-1'] }],
      [() => api.archiveStage('b-1', 's-1').subscribe(), 'POST', `${base}b-1/stages/s-1/archive/`, {}],
      [() => api.archiveStage('b-1', 's-1', 's-2').subscribe(), 'POST', `${base}b-1/stages/s-1/archive/`, { target_stage_id: 's-2' }],
    ];
    for (const [call, method, url, body] of cases) {
      call();
      const req = http.expectOne(url);
      expect(req.request.method).toBe(method);
      expect(req.request.body).toEqual(body);
      req.flush(dto);
    }
  });

  it('translates 400 field errors, 409 codes and network failures', () => {
    const errors: CrmApiError[] = [];
    api.create('X').subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(base).flush({ name: ['Ya existe.'] }, { status: 400, statusText: 'Bad Request' });
    api.archiveStage('b-1', 's-1').subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(`${base}b-1/stages/s-1/archive/`).flush(
      { detail: 'Tiene tarjetas.', code: 'stage_has_cards', card_count: 3 }, { status: 409, statusText: 'Conflict' });
    api.list().subscribe({ error: (e: CrmApiError) => errors.push(e) });
    http.expectOne(base).error(new ProgressEvent('error'));
    expect(errors[0].fieldErrors.name).toBe('Ya existe.');
    expect([errors[1].code, errors[1].cardCount, errors[1].message]).toEqual(['stage_has_cards', 3, 'Tiene tarjetas.']);
    expect(errors[2].status).toBe(0);
  });
});
