import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Commitment, PaymentRegistered, SourceKind } from '../../../shared/models/receivable';
import { CommitmentDetailComponent } from './commitment-detail.component';

const COMMITMENT = (kind: SourceKind = 'quotation', balance = '300.00'): Commitment => ({
  kind, number: kind === 'dental' ? 'ODO-000001' : 'PRO-000001', version: 1, status: 'presented', customer_id: 'c1',
  proforma_id: 'p1', customer_name: 'Rosa Pérez', date: '2026-11-03', currency: 'BOB', payment_status: 'pending',
  totals: { proposed: '350.00', accepted: '300.00', pending: '0.00', rejected: '50.00', paid: '0.00', balance },
  lines: [
    { line_id: 'l1', description: 'Limpieza', piece: '', decision: 'accepted', proposed: '100.00', accepted: '100.00', paid: '0.00', balance: '100.00', collectible: true },
    { line_id: 'l2', description: 'Corona', piece: '18', decision: 'accepted', proposed: '200.00', accepted: '200.00', paid: '0.00', balance: '200.00', collectible: true },
    { line_id: 'l3', description: 'Blanqueamiento', piece: '', decision: 'rejected', proposed: '50.00', accepted: '0.00', paid: '0.00', balance: '0.00', collectible: false },
  ],
  payments: [], allowed_actions: balance === '0.00' ? [] : ['register_payment'],
});

describe('CommitmentDetailComponent', () => {
  let http: HttpTestingController;

  function create(kind: SourceKind = 'quotation', balance = '300.00') {
    const number = kind === 'dental' ? 'ODO-000001' : 'PRO-000001';
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { paramMap: of(convertToParamMap({ kind, number })) } }],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(CommitmentDetailComponent);
    fixture.detectChanges();
    http.expectOne((req) => req.url.endsWith(`/receivables/commitments/${kind}/${number}/`)).flush(COMMITMENT(kind, balance));
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('muestra propuesto, aceptado, cobrado y saldo por separado y solo ofrece cobrar lo aceptado (AC-08)', () => {
    const text = (create().nativeElement as HTMLElement).textContent ?? '';
    for (const amount of ['Bs 350.00', 'Bs 300.00', 'Bs 0.00']) expect(text).toContain(amount);
    expect(text).toContain('Por cobrar');
  });

  it('«Registrar pago» abre el diálogo compartido y al pagar muestra el comprobante y relee el compromiso (AC-10)', () => {
    const fixture = create();
    const root = fixture.nativeElement as HTMLElement;
    const button = Array.from(root.querySelectorAll<HTMLButtonElement>('.card-header button')).find((b) => b.textContent?.trim() === 'Registrar pago');
    button?.click();
    http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/')).flush(COMMITMENT());
    fixture.componentInstance.onPaid({
      ...COMMITMENT('quotation', '200.00'), payment_status: 'partial', replayed: false,
      payment: { id: 'p', receipt_number: 'CB-000001', amount: '100.00', payment_method: 'CASH', payment_date: '2026-11-12', reference: '', recorded_by_name: 'ana', created_at: null, allocations: [] },
    } as PaymentRegistered);
    http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/')).flush(COMMITMENT('quotation', '200.00'));
    fixture.detectChanges();
    expect(root.textContent).toContain('CB-000001');
  });

  it('ofrece volver a la proforma con el id de la versión vigente (AC-10)', () => {
    const fixture = create();
    const link = (fixture.nativeElement as HTMLElement).querySelector('a[href="/pocketbiz/quotations/proformas/p1"]');
    expect(link).not.toBeNull();
    expect(fixture.componentInstance.patientLink).toBeNull();
  });

  it('en un compromiso dental dice «Paciente» y ofrece volver al paciente y a la proforma odontológica (AC-10, AC-11)', () => {
    const fixture = create('dental');
    const root = fixture.nativeElement as HTMLElement;
    expect(root.textContent).toContain('Paciente');
    expect(root.querySelector('a[href="/pocketbiz/dentistry/patients/c1"]')).not.toBeNull();
    expect(root.querySelector('a[href="/pocketbiz/dentistry/proformas/p1"]')).not.toBeNull();
  });

  it('sin saldo no ofrece registrar pago', () => {
    const root = create('quotation', '0.00').nativeElement as HTMLElement;
    expect(Array.from(root.querySelectorAll('.card-header button')).some((b) => b.textContent?.trim() === 'Registrar pago')).toBeFalse();
  });
});
