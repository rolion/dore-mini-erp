import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Commitment } from '../../../shared/models/receivable';
import { CommitmentDetailComponent } from './commitment-detail.component';

const COMMITMENT: Commitment = {
  kind: 'quotation', number: 'PRO-000001', version: 1, status: 'presented', customer_id: 'c1', proforma_id: 'p1',
  customer_name: 'Rosa Pérez', date: '2026-11-03', currency: 'BOB', payment_status: 'pending',
  totals: { proposed: '350.00', accepted: '300.00', pending: '0.00', rejected: '50.00', paid: '0.00', balance: '300.00' },
  lines: [
    { line_id: 'l1', description: 'Limpieza', piece: '', decision: 'accepted', proposed: '100.00', accepted: '100.00', paid: '0.00', balance: '100.00', collectible: true },
    { line_id: 'l2', description: 'Corona', piece: '18', decision: 'accepted', proposed: '200.00', accepted: '200.00', paid: '0.00', balance: '200.00', collectible: true },
    { line_id: 'l3', description: 'Blanqueamiento', piece: '', decision: 'rejected', proposed: '50.00', accepted: '0.00', paid: '0.00', balance: '0.00', collectible: false },
  ],
  payments: [], allowed_actions: ['register_payment'],
};

describe('CommitmentDetailComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(), provideHttpClientTesting(), provideRouter([]), ...provideTestTranslations(),
        { provide: ActivatedRoute, useValue: { paramMap: { subscribe: (fn: (p: unknown) => void) => { fn(convertToParamMap({ kind: 'quotation', number: 'PRO-000001' })); return { unsubscribe() {} }; }, pipe() { return this; } } } },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(CommitmentDetailComponent);
    fixture.detectChanges();
    http.expectOne((req) => req.url.endsWith('/receivables/commitments/quotation/PRO-000001/')).flush(COMMITMENT);
    fixture.detectChanges();
    return fixture;
  }

  afterEach(() => http.verify());

  it('muestra propuesto, aceptado, cobrado y saldo por separado y solo ofrece cobrar lo aceptado', () => {
    const fixture = create();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    for (const amount of ['Bs 350.00', 'Bs 300.00', 'Bs 0.00']) expect(text).toContain(amount);
    expect(fixture.componentInstance.payableLines.map((line) => line.line_id)).toEqual(['l1', 'l2']);
  });

  it('valida la distribución, pasa por el resumen y envía una sola vez con la misma clave', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.open();
    component.form.patchValue({ amount: '150.00' });
    component.distributeInOrder();
    expect(component.allocations.at(0).value.amount).toBe('100.00');
    expect(component.allocations.at(1).value.amount).toBe('50.00');
    expect(component.distributionError).toBe('');

    component.allocations.at(1).patchValue({ amount: '10.00' });
    expect(component.distributionError).not.toBe('');
    component.review();
    expect(component.step).toBe('form');

    component.allocations.at(1).patchValue({ amount: '50.00' });
    component.review();
    expect(component.step).toBe('summary');
    component.confirm();
    component.confirm(); // doble clic: no se envía otra petición
    const request = http.expectOne((req) => req.url.endsWith('/payments/'));
    expect(request.request.body.allocations).toEqual([{ line_id: 'l1', amount: '100.00' }, { line_id: 'l2', amount: '50.00' }]);
    const key = request.request.body.idempotency_key as string;
    request.flush({ ...COMMITMENT, payment_status: 'partial', totals: { ...COMMITMENT.totals, paid: '150.00', balance: '150.00' },
      payment: { id: 'p1', receipt_number: 'CB-000001', amount: '150.00', payment_method: 'CASH', payment_date: '2026-11-04', reference: '', recorded_by_name: 'ana', created_at: null, allocations: [] },
      replayed: false });
    fixture.detectChanges();
    expect(component.step).toBe('closed');
    expect(component.receipt?.receipt_number).toBe('CB-000001');
    expect(component.commitment?.totals.balance).toBe('150.00');
    expect(key.length).toBeGreaterThan(10);
  });

  it('conserva los datos y la clave ante un error del servidor para reintentar', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.open();
    component.form.patchValue({ amount: '100.00', reference: 'QR 1' });
    component.distributeInOrder();
    component.review();
    component.confirm();
    const first = http.expectOne((req) => req.url.endsWith('/payments/'));
    first.flush({}, { status: 500, statusText: 'Error' });
    expect(component.step).toBe('form');
    expect(component.failure?.message).toBeTruthy();
    expect(component.form.controls.reference.value).toBe('QR 1');
    component.review();
    component.confirm();
    const retry = http.expectOne((req) => req.url.endsWith('/payments/'));
    expect(retry.request.body.idempotency_key).toBe(first.request.body.idempotency_key);
    retry.flush({}, { status: 500, statusText: 'Error' });
  });

  it('tras un conflicto 409 recarga y reconstruye la distribución sin desalinear tratamientos', () => {
    const fixture = create();
    const component = fixture.componentInstance;
    component.open();
    component.form.patchValue({ amount: '150.00' });
    component.distributeInOrder();
    component.review();
    component.confirm();
    http.expectOne((req) => req.url.endsWith('/payments/')).flush({}, { status: 409, statusText: 'Conflict' });
    // Mientras tanto otra persona cobró del todo «Limpieza»: ya no es cobrable.
    const reloaded: Commitment = {
      ...COMMITMENT,
      lines: [{ ...COMMITMENT.lines[0], paid: '100.00', balance: '0.00', collectible: false }, ...COMMITMENT.lines.slice(1)],
    };
    http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/')).flush(reloaded);
    fixture.detectChanges();
    expect(component.saving).toBeFalse();
    expect(component.step).toBe('form');
    expect(component.allocations.length).toBe(component.payableLines.length);
    expect(component.allocations.length).toBe(1);
    expect(component.allocations.at(0).value.amount).toBe('');
    expect(component.form.controls.amount.value).toBe('150.00');
    component.review(); // distribución vacía: no pasa al resumen ni lanza errores
    expect(component.step).toBe('form');
  });
});
