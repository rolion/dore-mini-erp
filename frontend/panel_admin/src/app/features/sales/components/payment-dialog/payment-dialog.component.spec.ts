import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';

import { OrderApiError, OrderRuleError } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { NO_SALES_DEFAULTS, SalesDefaults, SalesSettingsService } from '../../services/sales-settings.service';
import { makeOrder } from '../../testing/order-fixtures';
import { PaymentDialogComponent, STALE_ORDER_FOR_PAYMENT } from './payment-dialog.component';

describe('PaymentDialogComponent', () => {
  let fixture: ComponentFixture<PaymentDialogComponent>;
  let component: PaymentDialogComponent;
  let element: HTMLElement;
  let api: jasmine.SpyObj<OrdersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  let defaults: SalesDefaults;

  function setup(): void {
    fixture = TestBed.createComponent(PaymentDialogComponent);
    component = fixture.componentInstance;
    component.init(makeOrder({ balance: '50.00' }));
    fixture.detectChanges();
    element = fixture.nativeElement as HTMLElement;
  }

  function fill(amount = '20.00'): void {
    component.form.patchValue({ amount, paymentMethod: 'QR', paymentDate: '2026-10-02', reference: ' ref-1 ' });
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['registerPayment']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    defaults = NO_SALES_DEFAULTS;
    TestBed.configureTestingModule({
      imports: [PaymentDialogComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: OrdersApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal },
        { provide: SalesSettingsService, useValue: { defaults: () => of(defaults) } },
      ],
    });
  });

  it('shows the order, its balance and the empty form (AC-13)', () => {
    setup();
    expect(element.querySelector('[data-testid="order-reference"]')?.textContent).toContain('P-1A2B3C4D');
    expect(element.querySelector('[data-testid="payment-balance-help"]')?.textContent).toContain('50.00');
    expect(component.form.controls.paymentMethod.value).toBe('CASH');
    expect((element.querySelector('[data-testid="confirm"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('preselects the default payment method of Sales (AC-13)', () => {
    defaults = { ...NO_SALES_DEFAULTS, paymentMethod: 'QR' };
    setup();
    expect(component.form.controls.paymentMethod.value).toBe('QR');
  });

  it('registers the payment and closes returning the updated order (AC-13)', () => {
    const updated = makeOrder({ paidTotal: '20.00' });
    api.registerPayment.and.returnValue(of(updated));
    setup();
    fill();
    component.submit();
    const [orderId, input] = api.registerPayment.calls.mostRecent().args;
    expect(orderId).toBe('o-1');
    expect(input).toEqual(jasmine.objectContaining({ amount: '20.00', paymentMethod: 'QR', paymentDate: '2026-10-02', reference: 'ref-1' }));
    expect(input.idempotencyKey).toBeTruthy();
    expect(modal.close).toHaveBeenCalledOnceWith(updated);
  });

  it('reuses the attempt key on a retry and changes it when the data changes (AC-13)', () => {
    api.registerPayment.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
    setup();
    fill();
    component.submit();
    component.submit();
    const [first, second] = api.registerPayment.calls.allArgs().map((args) => args[1].idempotencyKey);
    expect(first).toBe(second);
    component.form.controls.amount.setValue('21.00');
    component.submit();
    expect(api.registerPayment.calls.mostRecent().args[1].idempotencyKey).not.toBe(first);
  });

  it('shows server field errors in the modal without losing what was typed (AC-13)', () => {
    api.registerPayment.and.returnValue(
      throwError(() => new OrderApiError('Revisa', 400, { amount: ['No puede superar el saldo.'] })),
    );
    setup();
    fill('999.00');
    component.submit();
    fixture.detectChanges();
    expect(element.querySelector('[data-testid="amount-error"]')?.textContent).toContain('saldo');
    expect(component.form.controls.amount.value).toBe('999.00');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('explains missing accounting configuration and other failures without closing (AC-13)', () => {
    const issue = { code: 'x', subject: 'Cuenta', message: 'Falta la cuenta' };
    api.registerPayment.and.returnValue(
      throwError(() => new OrderRuleError('Falta configuración', 'posting_configuration_missing', [], '', [issue])),
    );
    setup();
    fill();
    component.submit();
    fixture.detectChanges();
    expect(component.postingIssues).toEqual([issue]);
    api.registerPayment.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
    component.submit();
    fixture.detectChanges();
    expect(element.querySelector('[data-testid="alert-error"]')?.textContent).toContain('Sin conexión');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('is dismissed as stale when the order no longer admits payments (AC-13)', () => {
    api.registerPayment.and.returnValue(throwError(() => new OrderRuleError('Cancelado', 'order_cancelled')));
    setup();
    fill();
    component.submit();
    expect(modal.dismiss).toHaveBeenCalledOnceWith(STALE_ORDER_FOR_PAYMENT);
  });

  it('does not submit twice while saving and cancels without writing (AC-13)', () => {
    setup();
    fill();
    component.saving = true;
    component.submit();
    expect(api.registerPayment).not.toHaveBeenCalled();
    component.saving = false;
    (element.querySelector('[data-testid="cancel"]') as HTMLButtonElement).click();
    expect(modal.dismiss).toHaveBeenCalled();
  });
});
