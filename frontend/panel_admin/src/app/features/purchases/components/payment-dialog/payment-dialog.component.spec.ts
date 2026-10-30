import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { NEVER, of, throwError } from 'rxjs';

import { PaymentApiError, PaymentMethod } from '../../models/payment';
import { PaymentsApiService } from '../../services/payments-api.service';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { makePayment } from '../../testing/payment-fixtures';
import { makeConfirmedPurchase } from '../../testing/purchase-fixtures';
import { PaymentDialogComponent } from './payment-dialog.component';

describe('PaymentDialogComponent', () => {
  let fixture: ComponentFixture<PaymentDialogComponent>;
  let component: PaymentDialogComponent;
  let api: jasmine.SpyObj<PaymentsApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  let purchasesApi: jasmine.SpyObj<PurchasesApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<PaymentsApiService>('PaymentsApiService', ['create']);
    purchasesApi = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get']);
    purchasesApi.get.and.returnValue(of(makeConfirmedPurchase({ balance: '25.00' })));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    await TestBed.configureTestingModule({
      imports: [PaymentDialogComponent],
      providers: [
        { provide: PaymentsApiService, useValue: api },
        { provide: PurchasesApiService, useValue: purchasesApi },
        { provide: NgbActiveModal, useValue: modal },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PaymentDialogComponent);
    component = fixture.componentInstance;
    component.init(makeConfirmedPurchase({ balance: '25.00' }));
    fixture.detectChanges();
  });

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector<HTMLElement>(`[data-testid="${id}"]`);

  function fill(amount: string, method: PaymentMethod = 'CASH'): void {
    component.form.patchValue({ amount, paymentMethod: method });
    fixture.detectChanges();
  }

  it('shows the current balance next to the amount and today as the default date (AC-17)', () => {
    expect(byId('balance')?.textContent).toContain('Bs 25.00');
    expect(component.form.controls.paymentDate.value).toBe(component.today);
  });

  it('requires amount, method and a non-future date before sending (AC-17)', () => {
    component.submit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(byId('amount-error')).not.toBeNull();
    expect(byId('method-error')).not.toBeNull();
    component.form.patchValue({ paymentDate: '2999-01-01' });
    fixture.detectChanges();
    expect(byId('date-error')?.textContent).toContain('futura');
  });

  it('does not let the amount exceed the balance (AC-17)', () => {
    fill('25.01');
    component.submit();
    fixture.detectChanges();
    expect(api.create).not.toHaveBeenCalled();
    expect(byId('amount-error')?.textContent).toContain('saldo pendiente');
  });

  it('fills the full balance with the shortcut (AC-17)', () => {
    byId('pay-in-full')?.click();
    expect(component.form.controls.amount.value).toBe('25.00');
  });

  it('sends the same payment id on every retry and closes on success (AC-18, AC-19)', () => {
    api.create.and.returnValues(
      throwError(() => new PaymentApiError('Ocurrió un error inesperado.', 500)),
      of(makePayment()),
    );
    fill('10.00', 'QR');
    component.submit();
    expect(modal.close).not.toHaveBeenCalled();
    component.submit();
    const [first, second] = api.create.calls.allArgs();
    expect(first[0]).toBe('c-1');
    expect(first[1].paymentId).toBe(second[1].paymentId);
    expect(second[1]).toEqual(jasmine.objectContaining({ amount: '10.00', paymentMethod: 'QR' }));
    expect(modal.close).toHaveBeenCalledWith(makePayment());
  });

  it('keeps the dialog open and the typed values on a server error (AC-18)', () => {
    api.create.and.returnValue(
      throwError(
        () =>
          new PaymentApiError('Revisa los datos ingresados.', 400, {
            amount: 'El monto no puede superar el saldo pendiente (Bs 5.00).',
          }),
      ),
    );
    fill('10.00', 'CARD');
    component.submit();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(byId('amount-error')?.textContent).toContain('saldo pendiente');
    expect(component.form.controls.amount.value).toBe('10.00');
    expect(component.form.controls.paymentMethod.value).toBe('CARD');
    expect(component.submitting).toBeFalse();
  });

  it('shows a general error when the server answers without field errors (AC-18)', () => {
    api.create.and.returnValue(throwError(() => new PaymentApiError('Solo una compra confirmada admite pagos.', 409)));
    fill('10.00');
    component.submit();
    fixture.detectChanges();
    expect(byId('general-error')?.textContent).toContain('Solo una compra confirmada admite pagos.');
  });

  it('disables the button while sending (AC-18)', () => {
    api.create.and.returnValue(NEVER);
    fill('10.00');
    component.submit();
    fixture.detectChanges();
    expect(component.submitting).toBeTrue();
    expect((byId('submit') as HTMLButtonElement).disabled).toBeTrue();
    expect(byId('submit')?.textContent).toContain('Registrando');
  });

  it('re-reads the purchase after a stale-balance rejection and keeps what was typed (REV-02)', () => {
    api.create.and.returnValue(
      throwError(
        () =>
          new PaymentApiError('Revisa los datos ingresados.', 400, {
            amount: 'El monto no puede superar el saldo pendiente (70.00).',
          }),
      ),
    );
    purchasesApi.get.and.returnValue(of(makeConfirmedPurchase({ balance: '70.00', paidTotal: '30.00' })));
    component.init(makeConfirmedPurchase({ balance: '100.00' }));
    fixture.detectChanges();
    const refreshed: string[] = [];
    component.purchaseRefreshed.subscribe((p) => refreshed.push(p.balance));
    fill('80.00', 'QR');
    component.submit();
    fixture.detectChanges();
    expect(purchasesApi.get).toHaveBeenCalledWith('c-1');
    expect(refreshed).toEqual(['70.00']);
    expect(byId('balance')?.textContent).toContain('Bs 70.00');
    byId('pay-in-full')?.click();
    expect(component.form.controls.amount.value).toBe('70.00');
    expect(component.form.controls.paymentMethod.value).toBe('QR');
    expect(modal.close).not.toHaveBeenCalled();
  });

  it('does not re-read the purchase after a success or a network error', () => {
    api.create.and.returnValue(throwError(() => new PaymentApiError('Sin conexión.', 0)));
    fill('10.00');
    component.submit();
    expect(purchasesApi.get).not.toHaveBeenCalled();
  });

  it('associates each error with its field for assistive technology (REV-03)', () => {
    component.submit();
    fixture.detectChanges();
    const amount = root().querySelector('#payment-amount');
    const method = root().querySelector('#payment-method');
    expect(amount?.getAttribute('aria-invalid')).toBe('true');
    expect(amount?.getAttribute('aria-describedby')).toBe('payment-amount-error');
    expect(root().querySelector('#payment-amount-error')?.getAttribute('role')).toBe('alert');
    expect(method?.getAttribute('aria-describedby')).toBe('payment-method-error');
    fill('10.00', 'CASH');
    expect(amount?.getAttribute('aria-invalid')).toBeNull();
    expect(amount?.getAttribute('aria-describedby')).toBeNull();
  });

  it('cancel dismisses without changes', () => {
    byId('back')?.click();
    expect(modal.dismiss).toHaveBeenCalled();
  });
});
