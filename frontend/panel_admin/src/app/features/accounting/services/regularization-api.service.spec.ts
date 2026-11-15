import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { RegularizationError, RegularizationSummary } from '../models/regularization';
import { makeSummaryDto } from '../testing/regularization-fixtures';
import { RegularizationApiService } from './regularization-api.service';

describe('RegularizationApiService', () => {
  let service: RegularizationApiService;
  let http: HttpTestingController;
  const request = { date_from: null, date_to: null, mapping: { CASH: [{ account_id: 'a-1' }] } };

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(RegularizationApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('previews without a confirmation and maps the summary (AC-15)', () => {
    let summary: RegularizationSummary | undefined;
    service.preview(request).subscribe((s) => (summary = s));
    const req = http.expectOne((r) => r.url.endsWith('/accounting/regularization/preview/'));
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toEqual(request);
    req.flush(makeSummaryDto());
    expect(summary?.totalPayments).toBe(4);
    expect(summary?.groups[0]).toEqual(jasmine.objectContaining({ status: 'missing', origin: 'PRODUCT', account: 'Caja', count: 2, amount: '125.00' }));
    expect(summary?.absentFields).toEqual({ author: 2 });
  });

  it('always sends confirm: true when applying (AC-16)', () => {
    service.apply(request).subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/accounting/regularization/apply/'));
    expect(req.request.body).toEqual({ ...request, confirm: true });
    req.flush(makeSummaryDto({ mode: 'apply' }));
  });

  it('turns a 400 into the list of server messages and a 409 into the in-progress error (AC-17)', () => {
    let bad: RegularizationError | undefined;
    service.preview(request).subscribe({ error: (e: RegularizationError) => (bad = e) });
    http.expectOne((r) => r.url.endsWith('preview/')).flush({ mapping: ['CASH: la cuenta no existe en la empresa.'] }, { status: 400, statusText: 'Bad Request' });
    expect(bad?.messages).toEqual(['CASH: la cuenta no existe en la empresa.']);

    let busy: RegularizationError | undefined;
    service.apply(request).subscribe({ error: (e: RegularizationError) => (busy = e) });
    http.expectOne((r) => r.url.endsWith('apply/')).flush({ detail: 'x', code: 'regularization_in_progress' }, { status: 409, statusText: 'Conflict' });
    expect(busy?.code).toBe('regularization_in_progress');
  });
});
