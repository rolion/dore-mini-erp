import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ExpensesApiError } from '../models/api-error';
import { ExpenseCategoryDto } from '../models/category';
import { CategoriesApiService } from './categories-api.service';

const DTO: ExpenseCategoryDto = {
  id: 'c1',
  name: 'Empaque',
  active: true,
  created_at: '2026-10-09T10:00:00Z',
  updated_at: '2026-10-09T10:00:00Z',
};

describe('CategoriesApiService', () => {
  let service: CategoriesApiService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(CategoriesApiService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('lists with the active filter and page size (AC-24)', () => {
    let name = '';
    service.list({ active: true, pageSize: 100 }).subscribe((page) => (name = page.results[0].name));
    const req = http.expectOne((r) => r.url === '/api/expense-categories/');
    expect(req.request.params.get('active')).toBe('true');
    expect(req.request.params.get('page_size')).toBe('100');
    req.flush({ count: 1, next: null, previous: null, results: [DTO] });
    expect(name).toBe('Empaque');
  });

  it('omits the active filter when asking for all', () => {
    service.list().subscribe();
    const req = http.expectOne('/api/expense-categories/');
    expect(req.request.params.has('active')).toBeFalse();
    req.flush({ count: 0, next: null, previous: null, results: [] });
  });

  it('creates, renames, activates and deactivates (AC-01, AC-02)', () => {
    service.create('Empaque').subscribe();
    let req = http.expectOne('/api/expense-categories/');
    expect([req.request.method, req.request.body]).toEqual(['POST', { name: 'Empaque' }]);
    req.flush(DTO);

    service.rename('c1', 'Embalaje').subscribe();
    req = http.expectOne('/api/expense-categories/c1/');
    expect([req.request.method, req.request.body]).toEqual(['PATCH', { name: 'Embalaje' }]);
    req.flush(DTO);

    service.deactivate('c1').subscribe();
    req = http.expectOne('/api/expense-categories/c1/deactivate/');
    expect(req.request.method).toBe('POST');
    req.flush({ ...DTO, active: false });

    service.activate('c1').subscribe();
    http.expectOne('/api/expense-categories/c1/activate/').flush(DTO);
  });

  it('exposes the name error of a duplicate (AC-01)', () => {
    let error: ExpensesApiError | null = null;
    service.create('Empaque').subscribe({ error: (err: ExpensesApiError) => (error = err) });
    http
      .expectOne('/api/expense-categories/')
      .flush({ name: ['Ya existe una categoría con ese nombre.'] }, { status: 400, statusText: 'Bad Request' });
    expect((error as unknown as ExpensesApiError).fieldErrors['name']).toEqual(['Ya existe una categoría con ese nombre.']);
  });
});
