import { HttpErrorResponse, provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../core/i18n/testing';
import { DecisionBody, DecisionFailure } from '../models/proforma-decisions';
import { ProformaDecisionsApiService, toDecisionFailure } from './proforma-decisions-api.service';

const BODY: DecisionBody = {
  idempotency_key: 'k-1', decision: 'accepted', line_ids: ['l1'], accepted_by_name: 'Ana', medium: 'in_person',
  reference: '', reason: '',
};

describe('ProformaDecisionsApiService', () => {
  let service: ProformaDecisionsApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    service = TestBed.inject(ProformaDecisionsApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('posts the decision with its idempotency key to each module', () => {
    service.decide('quotations/proformas', 'p1', BODY).subscribe();
    const first = http.expectOne(r => r.method === 'POST' && r.url.endsWith('/quotations/proformas/p1/decisions/'));
    expect(first.request.body).toEqual(BODY);
    first.flush({});
    service.decide('dentistry/proformas', 'p2', BODY).subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/dentistry/proformas/p2/decisions/')).flush({});
  });

  it('rectifies one line and reads the printable view', () => {
    service.rectify('dentistry/proformas', 'p1', 'l9', { ...BODY, decision: 'rejected', reason: 'x' }).subscribe();
    http.expectOne(r => r.method === 'POST' && r.url.endsWith('/dentistry/proformas/p1/lines/l9/rectify/')).flush({});
    service.printable('quotations/proformas', 'p1').subscribe();
    http.expectOne(r => r.method === 'GET' && r.url.endsWith('/quotations/proformas/p1/printable/')).flush({});
  });

  it('maps server errors to messages and keeps field errors', () => {
    let failure: DecisionFailure | undefined;
    service.decide('quotations/proformas', 'p1', BODY).subscribe({ error: (f: DecisionFailure) => failure = f });
    http.expectOne(r => r.url.endsWith('/decisions/')).flush({ medium: ['x'] }, { status: 400, statusText: 'Bad Request' });
    expect(failure?.fields['medium']).toContain('medio');
    expect(toDecisionFailure(new HttpErrorResponse({ status: 409 })).conflict).toBeTrue();
    expect(toDecisionFailure(new HttpErrorResponse({ status: 403 })).message).toContain('permiso');
    expect(toDecisionFailure(new Error('x')).message).not.toBe('');
  });
});
