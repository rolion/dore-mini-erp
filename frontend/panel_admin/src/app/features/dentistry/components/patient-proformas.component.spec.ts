import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { BehaviorSubject } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ModulesService } from '../../../core/service/modules.service';
import { PatientProformasComponent } from './patient-proformas.component';

const EMPTY_PAGE = { count: 0, next: null, previous: null, results: [] };
const ROW = (id: string, status: string) => ({
  id, number: 'ODO-000001', version: 1, status, customer_id: 'c-1', patient_name: 'Ana',
  date: '2026-11-04', valid_until: null, currency: 'BOB', total: '250.00',
});

describe('PatientProformasComponent', () => {
  let http: HttpTestingController;
  let keys: BehaviorSubject<ReadonlySet<string> | null>;

  function create(enabled: string[] | null, active = true) {
    keys = new BehaviorSubject<ReadonlySet<string> | null>(enabled ? new Set(enabled) : null);
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ModulesService, useValue: { enabledKeys$: keys.asObservable() } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(PatientProformasComponent);
    fixture.componentRef.setInput('patientId', 'c-1');
    fixture.componentRef.setInput('active', active);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('lists the proformas of the patient with their status, amounts and a new-proforma button', () => {
    const fixture = create(['services']);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/'))
      .flush({ ...EMPTY_PAGE, count: 2, results: [ROW('p1', 'presented'), ROW('p2', 'draft')] });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Presentada');
    expect(text).toContain('Borrador');
    expect(text).toContain('Bs 250.00');
    expect(text).toContain('04/11/2026');
    expect(text).toContain('Nueva proforma');
  });

  it('shows the empty state and an error with retry', () => {
    const fixture = create(['services']);
    http.expectOne(r => r.url.endsWith('/proformas/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('aún no tiene proformas');
    fixture.componentInstance.load(1);
    http.expectOne(r => r.url.endsWith('/proformas/')).flush({}, { status: 500, statusText: 'x' });
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No se pudieron cargar las proformas');
  });

  it('does not render or request anything while the Services module is disabled', () => {
    const fixture = create(['dentistry']);
    http.expectNone(r => r.url.includes('/proformas/'));
    expect((fixture.nativeElement as HTMLElement).textContent?.trim()).toBe('');
  });

  it('hides the new button and explains it for an archived patient, keeping the list', () => {
    const fixture = create(['services'], false);
    http.expectOne(r => r.url.endsWith('/proformas/')).flush({ ...EMPTY_PAGE, count: 1, results: [ROW('p1', 'presented')] });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('+ Nueva proforma');
    expect(text).toContain('archivado');
    expect(text).toContain('ODO-000001');
  });
});
