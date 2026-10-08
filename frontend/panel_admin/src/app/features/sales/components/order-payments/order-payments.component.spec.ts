import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { FieldErrors, Order, PaymentInput, todayIso } from '../../models/order';
import { makeOrder, makePayment } from '../../testing/order-fixtures';
import { OrderPaymentsComponent } from './order-payments.component';

describe('OrderPaymentsComponent', () => {
  let fixture: ComponentFixture<OrderPaymentsComponent>;
  let component: OrderPaymentsComponent;

  function render(order: Order, busy = false, errors: FieldErrors = {}): HTMLElement {
    fixture = TestBed.createComponent(OrderPaymentsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('order', order);
    fixture.componentRef.setInput('busy', busy);
    fixture.componentRef.setInput('errors', errors);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function openForm(): HTMLElement {
    component.open();
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [OrderPaymentsComponent] }));

  it('shows the empty state when there are no payments (AC-25)', () => {
    const element = render(makeOrder());
    expect(element.querySelector('[data-testid="payments-empty"]')?.textContent).toContain('Aún no hay pagos');
    expect(element.querySelector('table')).toBeNull();
  });

  it('lists the payments with date, method label, reference and amount, and the paid total (AC-12)', () => {
    const element = render(
      makeOrder({
        payments: [makePayment(), makePayment({ id: 'pay-2', paymentMethod: 'BANK_TRANSFER', reference: '', amount: '5.00' })],
        paidTotal: '25.00',
        paymentStatus: 'PARTIAL',
      }),
    );
    const rows = Array.from(element.querySelectorAll('[data-testid="payment-row"]')).map((row) =>
      Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim()),
    );
    expect(rows).toEqual([
      ['2026-10-02', 'QR', 'ref-1', 'Bs 20.00'],
      ['2026-10-02', 'Transferencia', '—', 'Bs 5.00'],
    ]);
    expect(element.querySelector('[data-testid="payments-total"]')?.textContent).toContain('Bs 25.00');
  });

  it('offers to register a payment only when the server says so (AC-12, AC-25)', () => {
    const allowed = render(makeOrder({ canRegisterPayment: true }));
    expect(allowed.querySelector('.card-header button')?.textContent).toContain('Registrar pago');
    const denied = render(makeOrder({ canRegisterPayment: false, status: 'CANCELLED', editable: false }));
    expect(denied.querySelector('.card-header button')).toBeNull();
  });

  it('opens an inline form with today as the default date, cash as method and the balance as help (AC-25)', () => {
    render(makeOrder({ balance: '70.00' }));
    const element = openForm();
    expect(element.querySelector('form')).not.toBeNull();
    expect(component.form.getRawValue()).toEqual({
      amount: '',
      paymentMethod: 'CASH',
      paymentDate: todayIso(),
      reference: '',
    });
    expect(element.querySelector('[data-testid="payment-balance-help"]')?.textContent).toContain('Bs 70.00');
    const options = Array.from(element.querySelectorAll('#payment-method option')).map((o) => o.textContent?.trim());
    expect(options).toEqual(['Efectivo', 'QR', 'Transferencia', 'Tarjeta', 'Otro']);
  });

  it('emits the typed payment with trimmed values (AC-12)', () => {
    render(makeOrder());
    openForm();
    const emitted: PaymentInput[] = [];
    component.paymentSubmit.subscribe((input) => emitted.push(input));
    component.form.setValue({ amount: ' 20.00 ', paymentMethod: 'QR', paymentDate: '2026-10-02', reference: ' ref ' });
    fixture.detectChanges();
    (fixture.debugElement.query(By.css('form button[type="submit"]')).nativeElement as HTMLButtonElement).click();
    expect(emitted).toEqual([{ amount: '20.00', paymentMethod: 'QR', paymentDate: '2026-10-02', reference: 'ref' }]);
  });

  it('does not emit without an amount or while busy (AC-12)', () => {
    render(makeOrder());
    openForm();
    const emitted: PaymentInput[] = [];
    component.paymentSubmit.subscribe((input) => emitted.push(input));
    component.submit();
    component.form.patchValue({ amount: '5.00' });
    fixture.componentRef.setInput('busy', true);
    component.submit();
    expect(emitted).toEqual([]);
  });

  it('closes and clears the form once the new payment arrives (AC-25)', () => {
    render(makeOrder());
    openForm();
    component.form.patchValue({ amount: '20.00' });
    fixture.componentRef.setInput(
      'order',
      makeOrder({ payments: [makePayment()], paidTotal: '20.00', balance: '50.00', paymentStatus: 'PARTIAL' }),
    );
    fixture.detectChanges();
    expect(component.formOpen()).toBeFalse();
    expect(component.form.getRawValue().amount).toBe('');
  });

  it('keeps the form open when the server rejects the payment and shows its errors (AC-12)', () => {
    render(makeOrder(), false, {
      amount: ['El monto no puede superar el saldo pendiente.'],
      paymentMethod: ['Inválido'],
      paymentDate: ['Futura'],
      reference: ['Larga'],
    });
    const element = openForm();
    expect(component.formOpen()).toBeTrue();
    expect(element.querySelector('[data-testid="amount-error"]')?.textContent).toContain('saldo pendiente');
    expect(element.querySelector('[data-testid="method-error"]')?.textContent).toContain('Inválido');
    expect(element.querySelector('[data-testid="date-error"]')?.textContent).toContain('Futura');
    expect(element.querySelector('[data-testid="reference-error"]')?.textContent).toContain('Larga');
  });

  it('closes the form when the order stops accepting payments (AC-11)', () => {
    render(makeOrder());
    openForm();
    fixture.componentRef.setInput('order', makeOrder({ canRegisterPayment: false, status: 'CANCELLED', editable: false }));
    fixture.detectChanges();
    expect(component.formOpen()).toBeFalse();
  });

  it('closes with Cancelar', () => {
    render(makeOrder());
    const element = openForm();
    (element.querySelector('form button[type="button"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(component.formOpen()).toBeFalse();
  });
});
