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

describe('PatientProformasComponent (cobro)', () => {
  let http: HttpTestingController;

  function create(enabled: string[]) {
    const keys = new BehaviorSubject<ReadonlySet<string> | null>(new Set(enabled));
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ModulesService, useValue: { enabledKeys$: keys.asObservable() } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(PatientProformasComponent);
    fixture.componentRef.setInput('patientId', 'c-1');
    fixture.detectChanges();
    return fixture;
  }

  const OBLIGATION = { kind: 'dental', number: 'ODO-000001', version: 1, customer_id: 'c-1', customer_name: 'Ana', accepted: '250.00',
    paid: '100.00', balance: '150.00', payment_status: 'partial', created_at: null, last_payment_date: '2026-11-04' };
  const PRESENTED = { ...ROW('p1', 'presented'), accepted_total: '250.00', collectible: true };

  afterEach(() => http.verify());

  it('con Cobros habilitado muestra Aceptado, Cobrado y Saldo y la acción «Cobrar» por fila (AC-09)', () => {
    const fixture = create(['services', 'receivables']);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/'))
      .flush({ ...EMPTY_PAGE, count: 2, results: [PRESENTED, { ...ROW('p2', 'draft'), number: 'ODO-000002', accepted_total: '0.00', collectible: false }] });
    const request = http.expectOne(r => r.url.endsWith('/receivables/obligations/'));
    expect(request.request.params.get('customer_id')).toBe('c-1');
    request.flush({ ...EMPTY_PAGE, count: 1, results: [OBLIGATION] });
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    const text = root.textContent ?? '';
    for (const header of ['Aceptado', 'Cobrado', 'Saldo']) expect(text).toContain(header);
    expect(text).toContain('Bs 100.00'); // cobrado
    expect(text).toContain('Bs 150.00'); // saldo = aceptado − cobrado
    const rows = root.querySelectorAll('tbody tr');
    expect(rows[0].textContent).toContain('Cobrar');
    expect(rows[1].textContent).not.toContain('Cobrar'); // borrador: sin cobro
    expect(rows[1].textContent).toContain('—');
  });

  it('sin obligación el cobrado es 0.00 y el saldo es lo aceptado', () => {
    const fixture = create(['services', 'receivables']);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/')).flush({ ...EMPTY_PAGE, count: 1, results: [PRESENTED] });
    http.expectOne(r => r.url.endsWith('/receivables/obligations/')).flush(EMPTY_PAGE);
    fixture.detectChanges();
    expect(fixture.componentInstance.collection(PRESENTED as never)).toEqual({ paid: '0.00', balance: '250.00' });
  });

  it('sin el módulo Cobros no hay columnas, acción ni lectura de cobros', () => {
    const fixture = create(['services']);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/')).flush({ ...EMPTY_PAGE, count: 1, results: [PRESENTED] });
    http.expectNone(r => r.url.includes('/receivables/'));
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).not.toContain('Saldo');
    expect(text).not.toContain('Cobrar');
  });

  it('si falla la lectura de cobros la tabla de proformas sigue visible con «—» y un aviso discreto', () => {
    const fixture = create(['services', 'receivables']);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/proformas/')).flush({ ...EMPTY_PAGE, count: 1, results: [PRESENTED] });
    http.expectOne(r => r.url.endsWith('/receivables/obligations/')).flush({}, { status: 500, statusText: 'x' });
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('ODO-000001');
    expect(text).toContain('No se pudo cargar el estado de cobro');
    expect(text).not.toContain('Cobrar');
  });
});
