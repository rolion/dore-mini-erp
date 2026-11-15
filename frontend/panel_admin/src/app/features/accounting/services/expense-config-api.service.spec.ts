import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ExpenseConfigApiService } from './expense-config-api.service';

describe('ExpenseConfigApiService', () => {
  let service: ExpenseConfigApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    service = TestBed.inject(ExpenseConfigApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists active categories with their classification', () => {
    let result: unknown;
    service.listCategories().subscribe((rows) => (result = rows));
    const req = http.expectOne((r) => r.url.endsWith('/expense-categories/'));
    expect(req.request.params.get('active')).toBe('true');
    req.flush({ count: 1, next: null, previous: null, results: [{ id: 'k1', name: 'Alquiler', classification: null }] });
    expect(result).toEqual([{ id: 'k1', name: 'Alquiler', classification: null }]);
  });

  it('sets and clears the category classification with PUT', () => {
    service.setCategoryClassification('k1', 'c1').subscribe();
    const req = http.expectOne((r) => r.url.endsWith('/expense-categories/k1/classification/'));
    expect(req.request.method).toBe('PUT');
    expect(req.request.body).toEqual({ classification_id: 'c1' });
    req.flush({ id: 'k1', name: 'Alquiler', classification: { id: 'c1', name: 'Alquiler', active: true } });
  });

  it('reports the first server message', () => {
    let message = '';
    service.setPaymentClassification('x').subscribe({ error: (e: Error) => (message = e.message) });
    http.expectOne((r) => r.url.endsWith('/purchases/payment-classification/')).flush(
      { classification_id: ['La clasificación está inactiva.'] },
      { status: 400, statusText: 'Bad Request' },
    );
    expect(message).toBe('La clasificación está inactiva.');
  });
});
