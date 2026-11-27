import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';
import { OrderApiError, OrderRuleError } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { makeOrder, makePayment, makeReturnPreview } from '../../testing/order-fixtures';
import { ReturnDialogComponent, STALE_ORDER_FOR_RETURN } from './return-dialog.component';

describe('ReturnDialogComponent', () => {
  let fixture: ComponentFixture<ReturnDialogComponent>;
  let component: ReturnDialogComponent;
  let api: jasmine.SpyObj<OrdersApiService>;
  let modal: jasmine.SpyObj<NgbActiveModal>;
  const order = makeOrder({ status: 'DELIVERED', allowedTransitions: ['return'] });
  const returned = makeOrder({ status: 'RETURNED', allowedTransitions: [] });

  function setup(preview = makeReturnPreview()): HTMLElement {
    fixture = TestBed.createComponent(ReturnDialogComponent);
    component = fixture.componentInstance;
    component.init(order, preview);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function q(id: string): HTMLElement | null {
    return (fixture.nativeElement as HTMLElement).querySelector(`[data-testid="${id}"]`);
  }

  function typeReason(value: string): void {
    component.form.controls.reason.setValue(value);
    fixture.detectChanges();
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['returnOrder']);
    modal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ReturnDialogComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: OrdersApiService, useValue: api },
        { provide: NgbActiveModal, useValue: modal },
      ],
    });
  });

  it('shows the products, the stock effect and the accounting effect before confirming (AC-11)', () => {
    setup();
    expect(q('order-reference')?.textContent).toContain('P-1A2B3C4D');
    expect(q('item-row')?.textContent).toContain('Bolsas');
    expect(q('stock-line')?.textContent).toContain('Bolsas: 2 u');
    expect(q('stock-effect')?.textContent).toContain('Central');
    expect(fixture.nativeElement.querySelectorAll('[data-testid="entry-line"]').length).toBe(2);
    expect(q('payments-effect')).toBeNull();
  });

  it('says the stock does not change when the order had no output (INV-04)', () => {
    setup(makeReturnPreview({ stock: null }));
    expect(q('stock-line')).toBeNull();
    expect(q('stock-effect')?.textContent).toContain('no tuvo salida');
  });

  it('needs a reason to confirm (INV-01)', () => {
    setup();
    expect((q('confirm') as HTMLButtonElement).disabled).toBeTrue();
    typeReason('   ');
    expect((q('confirm') as HTMLButtonElement).disabled).toBeTrue();
    typeReason('Defectuoso');
    expect((q('confirm') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('confirms with the trimmed reason and closes with the returned order (AC-03)', () => {
    api.returnOrder.and.returnValue(of(returned));
    setup();
    typeReason(' Defectuoso ');
    component.confirm();
    expect(api.returnOrder).toHaveBeenCalledOnceWith('o-1', 'Defectuoso', false);
    expect(modal.close).toHaveBeenCalledOnceWith(returned);
  });

  it('requires the refund confirmation when the order has payments (AC-02)', () => {
    setup(makeReturnPreview({
      requiresRefundAcknowledgement: true,
      payments: [{ id: 'pay-1', amount: '20.00', paymentMethod: 'QR', paymentDate: '2026-10-02' }],
    }));
    expect(q('payment-line')).not.toBeNull();
    typeReason('Defectuoso');
    expect((q('confirm') as HTMLButtonElement).disabled).toBeTrue();
    component.form.controls.refundAcknowledged.setValue(true);
    fixture.detectChanges();
    expect((q('confirm') as HTMLButtonElement).disabled).toBeFalse();
    api.returnOrder.and.returnValue(of(returned));
    component.confirm();
    expect(api.returnOrder).toHaveBeenCalledOnceWith('o-1', 'Defectuoso', true);
  });

  it('keeps the dialog open and shows the server message on a conflict (AC-04, AC-06)', () => {
    api.returnOrder.and.returnValue(throwError(() => new OrderRuleError('El período está cerrado.', 'fiscal_period_unavailable')));
    setup();
    typeReason('Defectuoso');
    component.confirm();
    fixture.detectChanges();
    expect(modal.close).not.toHaveBeenCalled();
    expect(q('alert-error')?.textContent).toContain('El período está cerrado.');
    expect(component.saving).toBeFalse();
    expect(component.form.controls.reason.value).toBe('Defectuoso');
  });

  it('dismisses as stale when the order already changed (AC-07)', () => {
    api.returnOrder.and.returnValue(throwError(() => new OrderRuleError('No permitido', 'invalid_transition')));
    setup();
    typeReason('Defectuoso');
    component.confirm();
    expect(modal.dismiss).toHaveBeenCalledOnceWith(STALE_ORDER_FOR_RETURN);
  });

  it('shows a generic server error', () => {
    api.returnOrder.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
    setup();
    typeReason('x');
    component.confirm();
    fixture.detectChanges();
    expect(q('alert-error')?.textContent).toContain('Sin conexión');
    expect(makePayment().id).toBe('pay-1');
  });
});
