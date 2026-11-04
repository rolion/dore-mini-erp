import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ProformaListComponent } from './proforma-list.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };
const ROW = {
  id: 'p1', number: 'PRO-000001', version: 1, status: 'draft', customer_id: 'c1', customer_name: 'Rosa',
  date: '2026-11-03', valid_until: null, currency: 'BOB', total: '250.00',
};

describe('ProformaListComponent', () => {
  let http: HttpTestingController;

  function create(query: Record<string, string> = {}) {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ProformaListComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('restores the filters from the URL and shows rows with dd/MM/yyyy dates and money', () => {
    const fixture = create({ status: 'draft', customer: 'rosa', page: '2' });
    const request = http.expectOne(req => req.url.endsWith('/quotations/proformas/'));
    expect(request.request.params.get('status')).toBe('draft');
    expect(request.request.params.get('customer')).toBe('rosa');
    expect(request.request.params.get('page')).toBe('2');
    request.flush({ ...EMPTY_PAGE, count: 1, results: [ROW] });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('PRO-000001');
    expect(text).toContain('03/11/2026');
    expect(text).toContain('Bs 250.00');
  });

  it('shows the empty state and an error with retry', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/quotations/proformas/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Aún no hay proformas');
    fixture.componentInstance.search();
    http.expectOne(req => req.url.endsWith('/quotations/proformas/'))
      .flush({}, { status: 500, statusText: 'Server Error' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudieron cargar las proformas.');
  });
});
