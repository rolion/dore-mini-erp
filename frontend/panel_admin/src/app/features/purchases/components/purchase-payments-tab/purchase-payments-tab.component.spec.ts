import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { Observable, Subject, of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { Payment, PaymentApiError } from '../../models/payment';
import { PaymentsApiService } from '../../services/payments-api.service';
import { makePayment } from '../../testing/payment-fixtures';
import { makeCancelledPurchase, makeConfirmedPurchase, makePurchase } from '../../testing/purchase-fixtures';
import { PurchasePaymentsTabComponent } from './purchase-payments-tab.component';

const page = (results: Payment[]): Page<Payment> => ({ count: results.length, next: null, previous: null, results });

describe('PurchasePaymentsTabComponent', () => {
  let fixture: ComponentFixture<PurchasePaymentsTabComponent>;
  let api: jasmine.SpyObj<PaymentsApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  let toastr: jasmine.SpyObj<ToastrService>;

  async function setup(
    purchase = makeConfirmedPurchase(),
    list: Observable<Page<Payment>> = of(page([])),
  ): Promise<void> {
    api = jasmine.createSpyObj<PaymentsApiService>('PaymentsApiService', ['list']);
    api.list.and.returnValue(list);
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [PurchasePaymentsTabComponent],
      providers: [
        { provide: PaymentsApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(PurchasePaymentsTabComponent);
    fixture.componentRef.setInput('purchase', purchase);
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const all = (id: string): HTMLElement[] => Array.from(root().querySelectorAll<HTMLElement>(`[data-testid="${id}"]`));
  const flush = (): Promise<void> => new Promise((resolve) => setTimeout(resolve));

  it('shows total, paid, balance and status, plus an explained empty state (AC-15)', async () => {
    await setup(makeConfirmedPurchase({ paymentStatus: 'partial', paidTotal: '10.00', balance: '15.00' }));
    expect(api.list).toHaveBeenCalledWith('c-1');
    expect(byId('total')?.textContent).toContain('Bs 25.00');
    expect(byId('paid-total')?.textContent).toContain('Bs 10.00');
    expect(byId('balance')?.textContent).toContain('Bs 15.00');
    expect(byId('payment-status')?.textContent).toContain('Pago parcial');
    expect(byId('payment-status')?.className).toContain('col-orange');
    expect(byId('empty')?.textContent).toContain('Aún no hay pagos registrados');
  });

  it('lists the payments with date, reference, amount, method and user (AC-15)', async () => {
    await setup(
      makeConfirmedPurchase(),
      of(
        page([
          makePayment(),
          makePayment({ id: 'pay-2', reference: 'PAG-2', amount: '5.50', paymentMethod: 'BANK_TRANSFER', userName: '' }),
        ]),
      ),
    );
    const rows = all('payment-row');
    expect(rows.length).toBe(2);
    for (const expected of ['30/10/2026', 'PAG-1A2B3C4D', 'Bs 10.00', 'Efectivo', 'ana']) {
      expect(rows[0].textContent).toContain(expected);
    }
    expect(rows[1].textContent).toContain('Transferencia');
    expect(rows[1].textContent).toContain('—');
  });

  it('offers Register payment only when the server allows it and explains otherwise (AC-16)', async () => {
    await setup(makeConfirmedPurchase());
    expect(byId('register')).not.toBeNull();
    expect(byId('blocked-reason')).toBeNull();
    TestBed.resetTestingModule();
    await setup(
      makeConfirmedPurchase({ allowedActions: ['receive'], paymentStatus: 'paid', paidTotal: '25.00', balance: '0.00' }),
    );
    expect(byId('register')).toBeNull();
    expect(byId('blocked-reason')?.textContent).toContain('Pagado');
    TestBed.resetTestingModule();
    await setup(makePurchase());
    expect(byId('register')).toBeNull();
    expect(byId('blocked-reason')?.textContent).toContain('Confirma la compra');
    expect(byId('empty')?.textContent).toContain('cuando la compra está confirmada');
    TestBed.resetTestingModule();
    await setup(makeCancelledPurchase());
    expect(byId('blocked-reason')?.textContent).toContain('cancelada');
  });

  it('has no way to delete, refund or collect by QR (AC-16)', async () => {
    await setup(makeConfirmedPurchase(), of(page([makePayment()])));
    const text = root().textContent ?? '';
    for (const forbidden of ['Eliminar', 'Borrar', 'Reembolso', 'Anular']) expect(text).not.toContain(forbidden);
  });

  it('refreshes the background while the dialog stays open after a stale-balance rejection (REV-02)', async () => {
    await setup();
    const refreshed = new Subject<void>();
    const instance = { init: jasmine.createSpy('init'), purchaseRefreshed: refreshed };
    modal.open.and.returnValue({ componentInstance: instance, result: new Promise(() => undefined) } as never);
    let emitted = 0;
    fixture.componentInstance.paid.subscribe(() => emitted++);
    byId('register')?.click();
    refreshed.next();
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(emitted).toBe(1);
    expect(toastr.success).not.toHaveBeenCalled();
  });

  it('registers through the dialog, then reloads the list and tells the detail (AC-19)', async () => {
    await setup();
    const instance = { init: jasmine.createSpy('init'), purchaseRefreshed: new Subject<void>() };
    modal.open.and.returnValue({ componentInstance: instance, result: Promise.resolve(makePayment()) } as never);
    let emitted = 0;
    fixture.componentInstance.paid.subscribe(() => emitted++);
    byId('register')?.click();
    await flush();
    expect(instance.init).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'c-1' }));
    expect(toastr.success).toHaveBeenCalledWith('Pago registrado');
    expect(api.list).toHaveBeenCalledTimes(2);
    expect(emitted).toBe(1);
  });

  it('does nothing when the dialog is cancelled', async () => {
    await setup();
    const instance = { init: jasmine.createSpy('init'), purchaseRefreshed: new Subject<void>() };
    modal.open.and.returnValue({ componentInstance: instance, result: Promise.reject(new Error('dismissed')) } as never);
    byId('register')?.click();
    await flush();
    expect(toastr.success).not.toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('shows a retryable error when the list cannot be loaded', async () => {
    await setup(
      makeConfirmedPurchase(),
      throwError(() => new PaymentApiError('No se pudo conectar con el servidor. Inténtalo de nuevo.', 0)),
    );
    expect(byId('error')?.textContent).toContain('No se pudo conectar');
    api.list.and.returnValue(of(page([makePayment()])));
    byId('retry')?.click();
    fixture.detectChanges();
    expect(all('payment-row').length).toBe(1);
  });
});
