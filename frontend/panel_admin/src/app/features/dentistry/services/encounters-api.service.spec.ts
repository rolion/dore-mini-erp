import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { EncountersApiService, encounterFailure } from './encounters-api.service';

describe('EncountersApiService', () => {
  let http: HttpTestingController;
  let api: EncountersApiService;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    http = TestBed.inject(HttpTestingController);
    api = TestBed.inject(EncountersApiService);
  });
  afterEach(() => http.verify());

  it('sends only the filters that have a value', () => {
    api.list({ from: '2030-01-07', to: '2030-01-07', professional: '', search: ' Ana ', status: '', encounter_status: 'pending', page: 2 }).subscribe();
    const request = http.expectOne(req => req.url.endsWith('/dentistry/appointments/'));
    expect(request.request.params.get('from')).toBe('2030-01-07');
    expect(request.request.params.get('search')).toBe('Ana');
    expect(request.request.params.get('encounter_status')).toBe('pending');
    expect(request.request.params.get('page')).toBe('2');
    expect(request.request.params.has('professional')).toBeFalse();
    request.flush({ count: 0, results: [], from: '', to: '' });
  });

  it('posts the cancellation reason and nothing for start or finish', () => {
    api.act('a1', 'cancel', 'Fiebre').subscribe();
    expect(http.expectOne(req => req.url.endsWith('/appointments/a1/encounter/cancel/')).request.body).toEqual({ reason: 'Fiebre' });
    api.act('a1', 'start').subscribe();
    expect(http.expectOne(req => req.url.endsWith('/appointments/a1/encounter/start/')).request.body).toEqual({});
  });

  it('translates stable server codes and falls back to the server message', () => {
    const conflict = (code: string, detail: string) => encounterFailure(new HttpErrorResponse({ status: 409, error: { detail, code } }));
    expect(conflict('draft_pending', 'x').message).toBe('Confirma o descarta el odontograma en borrador antes de finalizar.');
    expect(conflict('desconocido', 'Mensaje del servidor').message).toBe('Mensaje del servidor');
    expect(encounterFailure(new HttpErrorResponse({ status: 400, error: { reason: ['El motivo es obligatorio.'] } })).message).toBe('El motivo es obligatorio.');
    expect(encounterFailure(new HttpErrorResponse({ status: 403 })).status).toBe(403);
  });
});
