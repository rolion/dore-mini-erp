import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter, Router } from '@angular/router';
import { BehaviorSubject, of } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { ModulesService } from '../../../core/service/modules.service';
import { Commitment } from '../../../shared/models/receivable';
import { DentalProforma } from '../models/dental-proforma';
import { DentalProformaDetailComponent } from './dental-proforma-detail.component';

const DECISION_FIELDS = { line_kind: 'original', origin_line_id: null, decision: 'pending', decided_at: null,
  decision_detail: null, authorized: false } as const;

const PROFORMA = (status: DentalProforma['status'], actions: DentalProforma['allowed_actions']): DentalProforma => ({
  id: 'p1', number: 'ODO-000001', version: 1, status, customer_id: 'c-1', patient_name: 'Ana', date: '2026-11-04',
  valid_until: null, currency: 'BOB', total: '250.00', notes: '', can_edit_price: true, allowed_actions: actions,
  lines: [{ id: 'l1', service_id: 's1', description: 'Limpieza', quantity: '1.00', unit_price: '250.00', subtotal: '250.00', dental_piece: '18', ...DECISION_FIELDS },
    { id: 'l2', service_id: 's2', description: 'Corona', quantity: '1.00', unit_price: '0.00', subtotal: '0.00', dental_piece: '', ...DECISION_FIELDS }],
  versions: [{ id: 'p1', number: 'ODO-000001', version: 1, status, customer_id: 'c-1', patient_name: 'Ana', date: '2026-11-04',
    valid_until: null, currency: 'BOB', total: '250.00', accepted_total: '0.00', acceptance_status: 'pending' }],
  decision_actions: [], totals: { proposed: '250.00', accepted: '0.00', pending: '250.00', rejected: '0.00' },
  decision_history: [], previous_version_id: null, acceptance_status: 'pending', accepted_total: '0.00',
});

describe('DentalProformaDetailComponent', () => {
  let http: HttpTestingController;

  const PATIENT = (birth: string | null, responsible: string) => ({ id: 'c-1', customer: { id: 'c-1', name: 'Ana', birth_date: birth,
    responsible_name: responsible, responsible_phone: '' } });
  const COMMITMENT = (balance: string): Commitment => ({
    kind: 'dental', number: 'ODO-000001', version: 1, status: 'presented', customer_id: 'c-1', proforma_id: 'p1',
    customer_name: 'Ana', date: '2026-11-04', currency: 'BOB', payment_status: 'pending',
    totals: { proposed: '250.00', accepted: '250.00', pending: '0.00', rejected: '0.00', paid: '0.00', balance },
    lines: [], payments: [], allowed_actions: ['register_payment'],
  });

  function create(proforma: DentalProforma, enabled: string[] = [], patient = PATIENT(null, '')) {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ModulesService, useValue: { enabledKeys$: new BehaviorSubject<ReadonlySet<string> | null>(new Set(enabled)) } },
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ proformaId: 'p1' })) } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(DentalProformaDetailComponent);
    fixture.detectChanges();
    http.expectOne(r => r.url.endsWith('/dentistry/proformas/p1/')).flush(proforma);
    http.expectOne(r => r.url.endsWith('/dentistry/patients/c-1/')).flush(patient);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('shows the dental piece per line (or a dash), the status and the draft actions', () => {
    const fixture = create(PROFORMA('draft', ['edit', 'present']));
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Pieza dental');
    expect(text).toContain('18');
    expect(text).toContain('Borrador');
    expect(text).toContain('Presentar');
    expect(text).toContain('Editar');
    expect(text).not.toContain('Nueva versión');
  });

  it('presents with a confirmation dialog, shows the server error and keeps a double click from sending twice', () => {
    const fixture = create(PROFORMA('draft', ['edit', 'present']));
    const component = fixture.componentInstance;
    const dialog = (fixture.nativeElement as HTMLElement).querySelector('dialog') as HTMLDialogElement;
    component.open(dialog);
    component.present(dialog);
    component.present(dialog);
    const requests = http.match(r => r.method === 'POST' && r.url.endsWith('/present/'));
    expect(requests.length).toBe(1);
    requests[0].flush({ lines: ['x'] }, { status: 400, statusText: 'Bad Request' });
    expect(component.dialogError).toContain('línea');
    expect(component.saving).toBeFalse();
    component.present(dialog);
    http.expectOne(r => r.url.endsWith('/present/')).flush(PROFORMA('presented', ['new-version']));
    fixture.detectChanges();
    expect(component.proforma?.status).toBe('presented');
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('Nueva versión');
  });

  it('creates a new version and goes to editing the new draft', () => {
    const fixture = create(PROFORMA('presented', ['new-version']));
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fixture.componentInstance.newVersion();
    http.expectOne(r => r.url.endsWith('/new-version/')).flush({ ...PROFORMA('draft', ['edit', 'present']), id: 'p2', version: 2 });
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/dentistry/proformas', 'p2', 'editar']);
  });

  it('precarga como quien acepta al responsable si el paciente es menor, y al paciente si no (AC-03)', () => {
    const minor = create(PROFORMA('presented', []), [], PATIENT('2020-06-04', 'rodrigo leon'));
    expect(minor.componentInstance.acceptor).toBe('rodrigo leon');
    TestBed.resetTestingModule();
    const adult = create(PROFORMA('presented', []), [], PATIENT('1990-01-01', 'otra persona'));
    expect(adult.componentInstance.acceptor).toBe('Ana');
  });

  it('con Cobros habilitado muestra Cobrado y Saldo y «Cobrar» abre el diálogo sin navegar (AC-07, AC-08)', () => {
    const presented = { ...PROFORMA('presented', []), collectible: true, accepted_total: '250.00' };
    const fixture = create(presented, ['receivables']);
    http.expectOne(r => r.url.endsWith('/receivables/commitments/dental/ODO-000001/')).flush(COMMITMENT('250.00'));
    fixture.detectChanges();
    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).toContain('Saldo por cobrar');
    expect(root.textContent).not.toContain('El saldo de cobro no se calcula aquí');
    const button = Array.from(root.querySelectorAll<HTMLButtonElement>('.card-header button')).find(b => b.textContent?.trim() === 'Cobrar');
    expect(button).toBeDefined();
    button?.click();
    http.expectOne(r => r.url.endsWith('/receivables/commitments/dental/ODO-000001/')).flush(COMMITMENT('250.00'));
    fixture.detectChanges();
    expect(root.querySelector('app-payment-dialog dialog')).not.toBeNull();
    expect(root.querySelector('a[href*="receivables"]')).toBeNull();
  });

  it('sin el módulo Cobros no hay botón «Cobrar» ni lecturas de cobro (AC-07)', () => {
    const presented = { ...PROFORMA('presented', []), collectible: true, accepted_total: '250.00' };
    const fixture = create(presented, []);
    http.expectNone(r => r.url.includes('/receivables/'));
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Cobrar');
    expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Saldo por cobrar');
  });
});
