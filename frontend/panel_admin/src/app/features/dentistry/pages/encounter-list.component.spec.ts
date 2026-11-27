import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { listItem } from '../testing/encounter-fixtures';
import { EncounterListComponent } from './encounter-list.component';

describe('EncounterListComponent', () => {
  let http: HttpTestingController;

  function create(query: Record<string, string> = {}) {
    TestBed.configureTestingModule({
      providers: [
        ...provideTestTranslations(), provideHttpClient(), provideHttpClientTesting(), provideRouter([]),
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(EncounterListComponent);
    fixture.detectChanges();
    http.expectOne(req => req.url.includes('/professionals/')).flush({ count: 0, next: null, previous: null, results: [] });
    return fixture;
  }

  afterEach(() => http.verify());

  it('lists today\'s dental appointments with both statuses and a link to the encounter', () => {
    const fixture = create();
    const today = fixture.componentInstance.today();
    const request = http.expectOne(req => req.url.endsWith('/dentistry/appointments/'));
    expect(request.request.params.get('from')).toBe(today);
    expect(request.request.params.get('to')).toBe(today);
    request.flush({ count: 1, results: [listItem({ encounter_status: 'in_progress' })], from: today, to: today });
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain('C-000001');
    expect(element.textContent).toContain('Gestión 2026');
    expect(element.textContent).not.toContain('a1b2c3d4');
    expect(element.querySelector('th')?.textContent).toContain('Cita');
    expect(element.textContent).not.toContain('ID de cita');
    expect(element.textContent).toContain('Ana Pérez');
    expect(element.textContent).toContain('Dra. Rojas');
    expect(element.textContent).toContain('Confirmada');
    expect(element.textContent).toContain('En progreso');
    expect(element.querySelector('a[href="/pocketbiz/dentistry/appointments/a1b2c3d4-0000-0000-0000-000000000000"]')).not.toBeNull();
  });

  it('falls back to the short id for appointments created before the series', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/dentistry/appointments/')).flush({
      count: 1, results: [listItem({ code: null, fiscal_period_name: '' })], from: '', to: '' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('a1b2c3d4');
  });

  it('shows an empty state and keeps filters from the URL', () => {
    const fixture = create({ encounter_status: 'finished' });
    const request = http.expectOne(req => req.url.endsWith('/dentistry/appointments/'));
    expect(request.request.params.get('encounter_status')).toBe('finished');
    request.flush({ count: 0, results: [], from: '', to: '' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No hay citas con estos filtros.');
  });

  it('shows an error with retry when loading fails', () => {
    const fixture = create();
    http.expectOne(req => req.url.endsWith('/dentistry/appointments/')).flush({}, { status: 500, statusText: 'Error' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('[role="alert"]')?.textContent).toContain('No se pudieron cargar las citas.');
    fixture.componentInstance.search();
    http.expectOne(req => req.url.endsWith('/dentistry/appointments/')).flush({ count: 0, results: [], from: '', to: '' });
  });
});
