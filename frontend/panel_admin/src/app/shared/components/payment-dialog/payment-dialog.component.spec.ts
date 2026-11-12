import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { Component, ViewChild } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { Commitment, PaymentRegistered } from '../../models/receivable';
import { PaymentDialogComponent } from './payment-dialog.component';

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

@Component({
  imports: [PaymentDialogComponent],
  template: `<app-payment-dialog #dlg kind="quotation" number="PRO-000001" (paid)="result = $event" />`,
})
class HostComponent {
  @ViewChild('dlg', { static: true }) dialog!: PaymentDialogComponent;
  result: PaymentRegistered | null = null;
}

describe('PaymentDialogComponent', () => {
  let http: HttpTestingController;

  function create() {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting(), ...provideTestTranslations()] });
    http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    const dialog = fixture.componentInstance.dialog;
    dialog.open();
    http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/')).flush(COMMITMENT);
    fixture.detectChanges();
    return { fixture, dialog };
  }

  afterEach(() => http.verify());

  it('propone el total como monto y reparte en orden entre las líneas cobrables (AC-05)', () => {
    const { dialog } = create();
    expect(dialog.form.controls.amount.value).toBe('300.00');
    expect(dialog.shortcut).toBe('total');
    expect(dialog.appliedRows).toEqual([{ description: 'Limpieza', amount: '100.00' }, { description: 'Corona', amount: '200.00' }]);
    expect(dialog.validationError).toBe('');
  });

  it('atajos: 50 % del saldo y otro monto (INV-04)', () => {
    const { dialog } = create();
    dialog.setShortcut('half');
    expect(dialog.form.controls.amount.value).toBe('150.00');
    expect(dialog.shortcut).toBe('half');
    expect(dialog.appliedRows).toEqual([{ description: 'Limpieza', amount: '100.00' }, { description: 'Corona', amount: '50.00' }]);
    dialog.setShortcut('other');
    expect(dialog.form.controls.amount.value).toBe('');
    expect(dialog.canConfirm).toBeFalse();
  });

  it('un monto mayor que el saldo no se puede confirmar', () => {
    const { dialog } = create();
    dialog.form.patchValue({ amount: '300.01' });
    expect(dialog.validationError).not.toBe('');
    expect(dialog.canConfirm).toBeFalse();
  });

  it('confirma en un solo paso con imputaciones explícitas y una sola petición aunque se pulse dos veces (AC-05, AC-06)', () => {
    const { fixture, dialog } = create();
    dialog.setShortcut('half');
    dialog.confirm();
    dialog.confirm();
    const request = http.expectOne((req) => req.url.endsWith('/payments/'));
    expect(request.request.body.amount).toBe('150.00');
    expect(request.request.body.allocations).toEqual([{ line_id: 'l1', amount: '100.00' }, { line_id: 'l2', amount: '50.00' }]);
    expect(request.request.body.idempotency_key.length).toBeGreaterThan(10);
    const registered: PaymentRegistered = {
      ...COMMITMENT, payment_status: 'partial', totals: { ...COMMITMENT.totals, paid: '150.00', balance: '150.00' },
      payment: { id: 'pay1', receipt_number: 'CB-000001', amount: '150.00', payment_method: 'CASH', payment_date: '2026-11-12', reference: '', recorded_by_name: 'ana', created_at: null, allocations: [] },
      replayed: false,
    };
    request.flush(registered);
    fixture.detectChanges();
    expect(fixture.componentInstance.result?.payment.receipt_number).toBe('CB-000001');
  });

  it('distribución manual: la suma debe igualar el monto y envía lo editado', () => {
    const { dialog } = create();
    dialog.setShortcut('half');
    dialog.toggleManual();
    expect(dialog.allocations.length).toBe(2);
    expect(dialog.allocations.at(0).value.amount).toBe('100.00');
    dialog.allocations.at(0).patchValue({ amount: '40.00' });
    expect(dialog.validationError).not.toBe(''); // 40 + 50 ≠ 150
    dialog.allocations.at(1).patchValue({ amount: '110.00' });
    expect(dialog.validationError).toBe('');
    dialog.confirm();
    const request = http.expectOne((req) => req.url.endsWith('/payments/'));
    expect(request.request.body.allocations).toEqual([{ line_id: 'l1', amount: '40.00' }, { line_id: 'l2', amount: '110.00' }]);
    request.flush({}, { status: 500, statusText: 'Error' });
  });

  it('ante un error conserva los datos y la clave de idempotencia para reintentar', () => {
    const { dialog } = create();
    dialog.form.patchValue({ reference: 'QR 1' });
    dialog.confirm();
    const first = http.expectOne((req) => req.url.endsWith('/payments/'));
    first.flush({}, { status: 500, statusText: 'Error' });
    expect(dialog.failure?.message).toBeTruthy();
    expect(dialog.form.controls.reference.value).toBe('QR 1');
    dialog.confirm();
    const retry = http.expectOne((req) => req.url.endsWith('/payments/'));
    expect(retry.request.body.idempotency_key).toBe(first.request.body.idempotency_key);
    retry.flush({}, { status: 500, statusText: 'Error' });
  });

  it('tras un 409 recarga el compromiso y reconstruye la distribución sin desalinear tratamientos (REV-02)', () => {
    const { dialog } = create();
    dialog.toggleManual();
    dialog.confirm();
    http.expectOne((req) => req.url.endsWith('/payments/')).flush({}, { status: 409, statusText: 'Conflict' });
    const reloaded: Commitment = {
      ...COMMITMENT,
      lines: [{ ...COMMITMENT.lines[0], paid: '100.00', balance: '0.00', collectible: false }, ...COMMITMENT.lines.slice(1)],
      totals: { ...COMMITMENT.totals, balance: '200.00' },
    };
    http.expectOne((req) => req.url.endsWith('/commitments/quotation/PRO-000001/')).flush(reloaded);
    expect(dialog.saving).toBeFalse();
    expect(dialog.allocations.length).toBe(dialog.payableLines.length);
    expect(dialog.allocations.length).toBe(1);
    expect(dialog.allocations.at(0).value.amount).toBe('');
  });
});
