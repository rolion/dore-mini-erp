import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { AppointmentListComponent } from './appointment-list.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };

describe('AppointmentListComponent', () => {
  let http: HttpTestingController;
  let navigate: jasmine.Spy;

  function create(query: Record<string, string> = {}) {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    const fixture = TestBed.createComponent(AppointmentListComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.endsWith('/professionals/')).flush(EMPTY_PAGE);
    return fixture;
  }

  afterEach(() => http.verify());

  it('restores filters and page from the URL and asks the server for them', () => {
    const fixture = create({ from: '2030-01-07', status: 'confirmed', search: 'rosa', page: '2' });
    const request = http.expectOne(req => req.url.endsWith('/agenda/appointments/'));
    expect(request.request.params.get('from')).toBe('2030-01-07');
    expect(request.request.params.get('status')).toBe('confirmed');
    expect(request.request.params.get('search')).toBe('rosa');
    expect(request.request.params.get('page')).toBe('2');
    request.flush(EMPTY_PAGE);
    expect(fixture.componentInstance.filters.controls.search.value).toBe('rosa');
    expect(navigate.calls.mostRecent().args[1].queryParams).toEqual(jasmine.objectContaining({
      from: '2030-01-07', status: 'confirmed', search: 'rosa', page: 2, to: null,
    }));
  });

  it('explains an empty result with and without filters', () => {
    const fixture = create({ search: 'zzz' });
    http.expectOne(req => req.url.endsWith('/agenda/appointments/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No hay citas con esos filtros.');
    fixture.componentInstance.clear();
    http.expectOne(req => req.url.endsWith('/agenda/appointments/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Aún no hay citas registradas.');
  });

  it('shows a retryable error when the server fails', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/agenda/appointments/')).flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('No se pudieron cargar las citas.');
    expect(text).toContain('Reintentar');
  });
});
