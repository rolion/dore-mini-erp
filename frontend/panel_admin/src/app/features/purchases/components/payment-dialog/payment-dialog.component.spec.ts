import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
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
    api = jasmine.createSpyObj<PaymentsApiService>('PaymentsApiService', ['create', 'preview']);
    api.preview.and.returnValue(NEVER);
    purchasesApi = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get']);
    purchasesApi.get.and.returnValue(of(makeConfirmedPurchase({ balance: '25.00' })));
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    await TestBed.configureTestingModule({
      imports: [PaymentDialogComponent],
      providers: [...provideTestTranslations(), provideRouter([]),
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

  it('shows the missing accounting setup with a link to Purchases settings and closes the dialog when followed (UI-04)', () => {
    api.create.and.returnValue(throwError(() => new PaymentApiError(
      'Falta la cuenta del método.', 409, {}, 'posting_configuration_missing', [{ code: 'method_unconfigured', subject: 'Caja', message: 'Falta la cuenta del método.' }])));
    fill('10.00');
    component.submit();
    fixture.detectChanges();
    expect(byId('alert-posting-issues')?.textContent).toContain('Falta la cuenta del método.');
    expect(byId('general-error')).toBeNull();
    const link = byId('link-posting-settings') as HTMLAnchorElement | null;
    expect(link?.getAttribute('href')).toBe('/pocketbiz/purchases/settings?tab=posting');
    link?.addEventListener('click', (event) => event.preventDefault());
    link?.click();
    expect(modal.dismiss).toHaveBeenCalled();
  });

  it('shows a plain error for other failures and no accounting alert (UI-04)', () => {
    api.create.and.returnValue(throwError(() => new PaymentApiError('Ocurrió un error inesperado.', 500)));
    fill('10.00');
    component.submit();
    fixture.detectChanges();
    expect(byId('general-error')?.textContent).toContain('inesperado');
    expect(byId('alert-posting-issues')).toBeNull();
  });

  it('asks for the expected entry once amount and method are valid and shows the split and the lines (AC-18, UI-04)', fakeAsync(() => {
    api.preview.and.returnValue(of({
      covered: true, debtAmount: '15.00', advanceAmount: '10.00',
      lines: [
        { side: 'DEBIT', role: 'PAYABLE', accountName: 'Proveedores', amount: '15.00' },
        { side: 'CREDIT', role: 'MONEY', accountName: 'Caja', amount: '15.00' },
      ],
      issues: [],
    }));
    fill('25.00');
    expect(byId('preview-loading')).not.toBeNull();
    tick(300);
    fixture.detectChanges();
    expect(api.preview).toHaveBeenCalledTimes(1);
    expect(byId('preview-debt')?.textContent).toContain('Bs 15.00');
    expect(byId('preview-advance')?.textContent).toContain('Bs 10.00');
    expect(root().querySelectorAll('[data-testid="preview-line"]').length).toBe(2);
    expect(root().textContent).toContain('Proveedores');
  }));

  it('shows the issues known from the preview with the settings link and disables Register (REV-06, UI-04)', fakeAsync(() => {
    api.preview.and.returnValue(of({
      covered: true, debtAmount: '10.00', advanceAmount: '0.00', lines: [],
      issues: [{ code: 'method_unconfigured', subject: 'Caja', message: 'Falta la cuenta del método.' }],
    }));
    fill('10.00');
    tick(300);
    fixture.detectChanges();
    expect(byId('alert-posting-issues')?.textContent).toContain('Falta la cuenta del método.');
    expect(byId('link-posting-settings')?.getAttribute('href')).toBe('/pocketbiz/purchases/settings?tab=posting');
    expect((byId('submit') as HTMLButtonElement).disabled).toBeTrue();
  }));

  it('shows a readable error when the preview fails and still lets the payment be registered (REV-06, UI-04)', fakeAsync(() => {
    api.preview.and.returnValue(throwError(() => new PaymentApiError('Error', 500)));
    fill('10.00');
    tick(300);
    fixture.detectChanges();
    expect(byId('preview-error')?.getAttribute('role')).toBe('alert');
    expect((byId('submit') as HTMLButtonElement).disabled).toBeFalse();
  }));

  it('announces the loading state politely (REV-06, UI-04)', fakeAsync(() => {
    fill('10.00');
    expect(byId('preview-loading')?.getAttribute('role')).toBe('status');
    expect(byId('preview-loading')?.getAttribute('aria-live')).toBe('polite');
    tick(300);
  }));

  it('does not ask for a preview while the amount is invalid, and says so when the payment makes no entry (UI-04)', fakeAsync(() => {
    fill('abc');
    tick(300);
    expect(api.preview).not.toHaveBeenCalled();
    api.preview.and.returnValue(of({ covered: false, debtAmount: '10.00', advanceAmount: '0.00', lines: [], issues: [] }));
    fill('10.00');
    tick(300);
    fixture.detectChanges();
    expect(byId('preview-uncovered')).not.toBeNull();
  }));

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
