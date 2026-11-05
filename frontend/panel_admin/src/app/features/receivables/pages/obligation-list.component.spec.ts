import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ObligationListComponent } from './obligation-list.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };
const ROW = {
  kind: 'quotation', number: 'PRO-000001', version: 1, customer_id: 'c1', customer_name: 'Rosa', accepted: '300.00',
  paid: '150.00', balance: '150.00', payment_status: 'partial', created_at: null, last_payment_date: '2026-11-04',
};

describe('ObligationListComponent', () => {
  let http: HttpTestingController;

  function create(query: Record<string, string> = {}) {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(ObligationListComponent);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('restaura los filtros de la URL y muestra importes y fechas', () => {
    const fixture = create({ status: 'partial', customer_id: 'c1' });
    const request = http.expectOne((req) => req.url.endsWith('/receivables/obligations/'));
    expect(request.request.params.get('status')).toBe('partial');
    expect(request.request.params.get('customer_id')).toBe('c1');
    request.flush({ ...EMPTY_PAGE, count: 1, results: [ROW] });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    for (const expected of ['PRO-000001', 'Bs 150.00', '04/11/2026', 'Parcial']) expect(text).toContain(expected);
  });

  it('muestra el estado vacío y un error con reintento', () => {
    const fixture = create();
    http.expectOne((req) => req.url.endsWith('/receivables/obligations/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Aún no hay cobros');
    fixture.componentInstance.search();
    http.expectOne((req) => req.url.endsWith('/receivables/obligations/')).flush({}, { status: 500, statusText: 'x' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudo cargar la lista de cobros.');
  });
});
