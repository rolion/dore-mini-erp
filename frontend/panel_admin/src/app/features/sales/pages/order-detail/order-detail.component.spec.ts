import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';
import Swal, { SweetAlertResult } from 'sweetalert2';

import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../../products';
import { FieldErrors, Order, OrderApiError, OrderItem, OrderRuleError } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { makeItem, makeOrder, makePayment } from '../../testing/order-fixtures';
import { OrderDetailComponent } from './order-detail.component';

interface DialogHooks {
  askDeliveryDate(order: Order): Promise<string | null>;
  askCancelReason(order: Order): Promise<string | null>;
  confirmRemove(item: OrderItem): Promise<boolean>;
}

const EMPTY_PRODUCTS: Page<never> = { count: 0, next: null, previous: null, results: [] };

describe('OrderDetailComponent', () => {
  let fixture: ComponentFixture<OrderDetailComponent>;
  let component: OrderDetailComponent;
  let api: jasmine.SpyObj<OrdersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;
  let navigate: jasmine.Spy;

  function setup(order: Order = makeOrder()): HTMLElement {
    api.get.and.returnValue(of(order));
    fixture = TestBed.createComponent(OrderDetailComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function dialogs(): DialogHooks {
    return component as unknown as DialogHooks;
  }

  function q(element: HTMLElement, id: string): HTMLElement | null {
    return element.querySelector(`[data-testid="${id}"]`);
  }

  function text(element: HTMLElement, id: string): string {
    return q(element, id)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', [
      'get', 'prepare', 'ready', 'deliver', 'cancel', 'addItem', 'changeItemQuantity', 'removeItem',
      'applyDiscount', 'registerPayment',
    ]);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    const products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    products.list.and.returnValue(of(EMPTY_PRODUCTS));

    TestBed.configureTestingModule({
      imports: [OrderDetailComponent],
      providers: [
        provideRouter([]),
        { provide: OrdersApiService, useValue: api },
        { provide: ProductsApiService, useValue: products },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'o-1' }) } } },
      ],
    });
    router = TestBed.inject(Router);
    navigate = spyOn(router, 'navigate').and.resolveTo(true);
  });

  describe('loading', () => {
    it('loads the order by the id in the route (AC-17, AC-25)', () => {
      setup();
      expect(api.get).toHaveBeenCalledOnceWith('o-1');
      expect(component.order?.id).toBe('o-1');
    });

    it('warns and goes back to the list when the order does not exist (EDGE-12)', () => {
      api.get.and.returnValue(throwError(() => new OrderApiError('Pedido no encontrado.', 404)));
      fixture = TestBed.createComponent(OrderDetailComponent);
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledWith('Pedido no encontrado.');
      expect(navigate).toHaveBeenCalledWith(['/sales/orders']);
    });

    it('shows a loading message until the order arrives', () => {
      const pending = new Subject<Order>();
      api.get.and.returnValue(pending);
      fixture = TestBed.createComponent(OrderDetailComponent);
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).toContain('Cargando');
      pending.next(makeOrder());
      fixture.detectChanges();
      expect((fixture.nativeElement as HTMLElement).textContent).not.toContain('Cargando');
    });
  });

  describe('two independent axes (AC-25, REQ-SAL-016)', () => {
    it('shows delivery and payment in separate panels with their own badges and dates', () => {
      const element = setup(
        makeOrder({ paymentStatus: 'PARTIAL', paidTotal: '20.00', balance: '50.00', expectedDeliveryDate: '2026-10-05' }),
      );
      const delivery = q(element, 'delivery-panel') as HTMLElement;
      const payment = q(element, 'payment-panel') as HTMLElement;
      expect(delivery.textContent).toContain('Nuevo');
      expect(delivery.querySelector('i.fa-truck')).not.toBeNull();
      expect(text(delivery, 'expected-date')).toBe('05/10/2026');
      expect(payment.textContent).toContain('Parcial');
      expect(payment.querySelector('i.fa-coins')).not.toBeNull();
      expect(text(payment, 'paid-of-total')).toBe('Pagado Bs 20.00 de Bs 70.00');
      expect(text(payment, 'balance-panel')).toBe('Saldo Bs 50.00');
    });

    it('shows "Sin saldo" when nothing is owed and the real delivery date once delivered', () => {
      const element = setup(
        makeOrder({
          status: 'DELIVERED', editable: false, allowedTransitions: [], paymentStatus: 'PAID', paidTotal: '70.00',
          balance: '0.00', deliveredDate: '2026-10-06',
        }),
      );
      expect(text(element, 'balance-panel')).toBe('Sin saldo');
      expect(text(element, 'delivered-date')).toBe('06/10/2026');
    });

    it('warns about a delivered order with pending balance, without the other alerts', () => {
      const element = setup(
        makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: [], balance: '70.00' }),
      );
      expect(text(element, 'alert-delivered-balance')).toContain('Entregado con saldo pendiente de Bs 70.00');
      expect(q(element, 'alert-paid-pending')).toBeNull();
      expect(q(element, 'alert-cancelled')).toBeNull();
    });

    it('informs about a paid order still waiting for delivery', () => {
      for (const status of ['NEW', 'IN_PREPARATION', 'READY'] as const) {
        const element = setup(makeOrder({ status, paymentStatus: 'PAID', paidTotal: '70.00', balance: '0.00' }));
        expect(text(element, 'alert-paid-pending')).toBe('Pagado, pendiente de entrega.');
        expect(q(element, 'alert-delivered-balance')).toBeNull();
      }
    });

    it('shows no balance alert for a delivered and paid order', () => {
      const element = setup(
        makeOrder({ status: 'DELIVERED', paymentStatus: 'PAID', paidTotal: '70.00', balance: '0.00', allowedTransitions: [] }),
      );
      expect(q(element, 'alert-delivered-balance')).toBeNull();
      expect(q(element, 'alert-paid-pending')).toBeNull();
    });

    it('shows the cancellation with its reason and that payments are kept', () => {
      const element = setup(
        makeOrder({
          status: 'CANCELLED', editable: false, allowedTransitions: [], canRegisterPayment: false,
          cancellationReason: 'Cliente desistió', payments: [makePayment()], paidTotal: '20.00', balance: '50.00',
          paymentStatus: 'PARTIAL',
        }),
      );
      const alert = text(element, 'alert-cancelled');
      expect(alert).toContain('Pedido cancelado');
      expect(alert).toContain('Cliente desistió');
      expect(alert).toContain('Los pagos registrados se conservan');
      expect(q(element, 'alert-delivered-balance')).toBeNull();
    });
  });

  describe('data and amounts', () => {
    it('shows customer (linked), channel label, dates and notes (AC-17)', () => {
      const element = setup(makeOrder({ salesChannel: 'STORE', notes: 'Sin picante' }));
      expect(q(element, 'customer')?.querySelector('a')?.getAttribute('href')).toBe('/customers/c-1');
      const text = element.textContent ?? '';
      expect(text).toContain('Venta directa');
      expect(text).toContain('01/10/2026');
      expect(text).toContain('Sin picante');
      expect(text).toContain('P-1A2B3C4D');
    });

    it('shows "Sin cliente" and "Sin notas" when there are none', () => {
      const element = setup(makeOrder({ customer: null, notes: '' }));
      expect(text(element, 'customer')).toBe('Sin cliente');
      expect(element.textContent).toContain('Sin notas');
    });

    it('shows the amounts exactly as the server returned them (AC-25, UI-05)', () => {
      const element = setup(makeOrder({ subtotal: '107.50', discount: '7.50', total: '100.00', balance: '100.00' }));
      expect(text(element, 'subtotal')).toBe('Bs 107.50');
      expect(text(element, 'total')).toBe('Bs 100.00');
    });
  });

  describe('actions follow what the server allows (AC-25)', () => {
    it('shows "Iniciar preparación" and "Cancelar pedido" for a NEW order', () => {
      const element = setup();
      expect(text(element, 'primary-action')).toBe('Iniciar preparación');
      expect(q(element, 'cancel-action')).not.toBeNull();
    });

    it('shows the matching primary action for each state', () => {
      const cases: [Partial<Order>, string][] = [
        [{ status: 'IN_PREPARATION', allowedTransitions: ['ready', 'cancel'] }, 'Marcar listo'],
        [{ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }, 'Marcar entregado'],
      ];
      for (const [overrides, label] of cases) {
        expect(text(setup(makeOrder(overrides)), 'primary-action')).toBe(label);
      }
    });

    it('shows no primary action nor cancel for terminal orders and hides what is not allowed', () => {
      for (const status of ['DELIVERED', 'CANCELLED'] as const) {
        const element = setup(makeOrder({ status, editable: false, allowedTransitions: [], canRegisterPayment: false }));
        expect(q(element, 'primary-action')).toBeNull();
        expect(q(element, 'cancel-action')).toBeNull();
        expect(q(element, 'edit-link')).toBeNull();
      }
    });

    it('does not infer actions from the status: only from allowed_transitions', () => {
      const element = setup(makeOrder({ status: 'NEW', allowedTransitions: ['cancel'] }));
      expect(q(element, 'primary-action')).toBeNull();
      expect(q(element, 'cancel-action')).not.toBeNull();
    });

    it('links "Editar datos" only while the order is editable (AC-24)', () => {
      const editable = setup();
      expect(q(editable, 'edit-link')?.getAttribute('href')).toBe('/sales/orders/o-1/edit');
      expect(q(setup(makeOrder({ editable: false })), 'edit-link')).toBeNull();
    });
  });

  describe('state changes', () => {
    it('prepares the order and shows the answer from the server (AC-09)', () => {
      const updated = makeOrder({ status: 'IN_PREPARATION', allowedTransitions: ['ready', 'cancel'] });
      api.prepare.and.returnValue(of(updated));
      const element = setup();
      (q(element, 'primary-action') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(api.prepare).toHaveBeenCalledOnceWith('o-1');
      expect(component.order).toBe(updated);
      expect(text(element, 'primary-action')).toBe('Marcar listo');
      expect(toastr.success).toHaveBeenCalledWith('Pedido en preparación');
    });

    it('marks the order ready', () => {
      api.ready.and.returnValue(of(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] })));
      setup(makeOrder({ status: 'IN_PREPARATION', allowedTransitions: ['ready', 'cancel'] }));
      component.runPrimary();
      expect(api.ready).toHaveBeenCalledOnceWith('o-1');
    });

    it('delivers with the date chosen in the dialog and warns about the balance (AC-25)', fakeAsync(() => {
      const delivered = makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: [], deliveredDate: '2026-10-03' });
      api.deliver.and.returnValue(of(delivered));
      setup(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      const ask = spyOn(dialogs(), 'askDeliveryDate').and.resolveTo('2026-10-03');
      component.runPrimary();
      flushMicrotasks();
      expect(ask).toHaveBeenCalledOnceWith(jasmine.objectContaining({ id: 'o-1', status: 'READY' }));
      expect(api.deliver).toHaveBeenCalledOnceWith('o-1', '2026-10-03');
      expect(component.order?.status).toBe('DELIVERED');
    }));

    it('does not deliver when the dialog is dismissed', fakeAsync(() => {
      setup(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      spyOn(dialogs(), 'askDeliveryDate').and.resolveTo(null);
      component.runPrimary();
      flushMicrotasks();
      expect(api.deliver).not.toHaveBeenCalled();
    }));

    it('cancels with the reason typed in the dialog (AC-11)', fakeAsync(() => {
      const cancelled = makeOrder({ status: 'CANCELLED', editable: false, allowedTransitions: [], cancellationReason: 'No lo quiere' });
      api.cancel.and.returnValue(of(cancelled));
      const element = setup();
      spyOn(dialogs(), 'askCancelReason').and.resolveTo('No lo quiere');
      (q(element, 'cancel-action') as HTMLButtonElement).click();
      flushMicrotasks();
      fixture.detectChanges();
      expect(api.cancel).toHaveBeenCalledOnceWith('o-1', 'No lo quiere');
      expect(q(element, 'alert-cancelled')).not.toBeNull();
    }));

    it('does not cancel when the user goes back', fakeAsync(() => {
      setup();
      spyOn(dialogs(), 'askCancelReason').and.resolveTo(null);
      void component.cancel();
      flushMicrotasks();
      expect(api.cancel).not.toHaveBeenCalled();
    }));

    it('disables the buttons while a request is in flight and ignores a second click (AC-25)', () => {
      const pending = new Subject<Order>();
      api.prepare.and.returnValue(pending);
      const element = setup();
      component.runPrimary();
      fixture.detectChanges();
      expect((q(element, 'primary-action') as HTMLButtonElement).disabled).toBeTrue();
      expect((q(element, 'cancel-action') as HTMLButtonElement).disabled).toBeTrue();
      component.runPrimary();
      expect(api.prepare).toHaveBeenCalledTimes(1);
      pending.next(makeOrder({ status: 'IN_PREPARATION', allowedTransitions: ['ready', 'cancel'] }));
      pending.complete();
      fixture.detectChanges();
      expect(component.busy).toBeFalse();
    });
  });

  describe('errors', () => {
    it('shows a rule conflict from the server and reloads the order (409)', () => {
      api.prepare.and.returnValue(throwError(() => new OrderRuleError('Un pedido necesita productos.', 'empty_order')));
      setup();
      component.runPrimary();
      expect(toastr.error).toHaveBeenCalledWith('Un pedido necesita productos.');
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(component.order).not.toBeNull();
      expect(component.busy).toBeFalse();
    });

    it('keeps field errors for the children and does not toast them (400)', () => {
      const errors: FieldErrors = { discount: ['No puede superar el subtotal.'] };
      api.applyDiscount.and.returnValue(throwError(() => new OrderApiError('Revisa los datos.', 400, errors)));
      const element = setup();
      component.applyDiscount('999.00');
      fixture.detectChanges();
      expect(component.fieldErrors).toEqual(errors);
      expect(toastr.error).not.toHaveBeenCalled();
      expect(text(element, 'discount-error')).toBe('No puede superar el subtotal.');
    });

    it('clears previous field errors on the next action', () => {
      api.applyDiscount.and.returnValues(
        throwError(() => new OrderApiError('x', 400, { discount: ['Mal'] })),
        of(makeOrder({ discount: '5.00', total: '65.00' })),
      );
      setup();
      component.applyDiscount('999');
      component.applyDiscount('5.00');
      expect(component.fieldErrors).toEqual({});
      expect(component.order?.discount).toBe('5.00');
    });

    it('toasts a network error without reloading', () => {
      api.prepare.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
      setup();
      component.runPrimary();
      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
      expect(api.get).toHaveBeenCalledTimes(1);
    });
  });

  describe('dialogs show user data as text, never as HTML (EDGE-15, REV-01)', () => {
    const NAME = '<img src=x onerror="window.__xss=1">';

    it('shows the product name of the remove dialog as plain text', async () => {
      setup();
      const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as SweetAlertResult);
      const confirmed = await (component as unknown as DialogHooks).confirmRemove(makeItem({ productName: NAME }));
      expect(confirmed).toBeTrue();
      const options = fire.calls.mostRecent().args[0] as unknown as Record<string, unknown>;
      expect(options['titleText']).toBe(`¿Quitar "${NAME}"?`);
      expect(options['title']).toBeUndefined();
      expect(options['html']).toBeUndefined();
    });

    it('keeps the delivery and cancellation dialogs free of user HTML', async () => {
      setup();
      const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: false } as SweetAlertResult);
      await (component as unknown as DialogHooks).askDeliveryDate(makeOrder());
      await (component as unknown as DialogHooks).askCancelReason(makeOrder({ payments: [makePayment()] }));
      for (const call of fire.calls.allArgs()) {
        expect((call[0] as unknown as Record<string, unknown>)['html']).toBeUndefined();
      }
    });

    it('returns the typed reason and date only when the dialogs are confirmed', async () => {
      setup();
      const fire = spyOn(Swal, 'fire');
      fire.and.resolveTo({ isConfirmed: true, value: ' Motivo ' } as SweetAlertResult);
      expect(await (component as unknown as DialogHooks).askCancelReason(makeOrder())).toBe('Motivo');
      fire.and.resolveTo({ isConfirmed: true, value: '2026-10-03' } as SweetAlertResult);
      expect(await (component as unknown as DialogHooks).askDeliveryDate(makeOrder())).toBe('2026-10-03');
      fire.and.resolveTo({ isConfirmed: false } as SweetAlertResult);
      expect(await (component as unknown as DialogHooks).askCancelReason(makeOrder())).toBeNull();
      expect(await (component as unknown as DialogHooks).askDeliveryDate(makeOrder())).toBeNull();
    });

    it('does not offer a balance warning when nothing is owed', async () => {
      setup();
      const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: false } as SweetAlertResult);
      await (component as unknown as DialogHooks).askDeliveryDate(makeOrder({ balance: '0.00' }));
      expect((fire.calls.mostRecent().args[0] as unknown as Record<string, unknown>)['text']).toBeUndefined();
      await (component as unknown as DialogHooks).askDeliveryDate(makeOrder({ balance: '70.00' }));
      expect((fire.calls.mostRecent().args[0] as unknown as Record<string, unknown>)['text']).toBe(
        'Quedará un saldo de Bs 70.00 por cobrar.',
      );
    });
  });

  describe('items, discount and payments', () => {
    it('adds a product with its quantity (AC-03)', () => {
      api.addItem.and.returnValue(of(makeOrder({ items: [makeItem(), makeItem({ id: 'i-2', productId: 'p-2' })] })));
      setup();
      component.addItem({ productId: 'p-2', quantity: 3 });
      expect(api.addItem).toHaveBeenCalledOnceWith('o-1', 'p-2', 3);
      expect(component.order?.items.length).toBe(2);
    });

    it('changes a quantity (AC-04)', () => {
      api.changeItemQuantity.and.returnValue(of(makeOrder()));
      setup();
      component.changeQuantity({ item: makeItem(), quantity: 5 });
      expect(api.changeItemQuantity).toHaveBeenCalledOnceWith('o-1', 'i-1', 5);
    });

    it('removes an item only after confirming (AC-05)', fakeAsync(() => {
      api.removeItem.and.returnValue(of(makeOrder({ items: [] })));
      setup();
      const confirm = spyOn(dialogs(), 'confirmRemove').and.resolveTo(false);
      void component.removeItem(makeItem());
      flushMicrotasks();
      expect(api.removeItem).not.toHaveBeenCalled();
      confirm.and.resolveTo(true);
      void component.removeItem(makeItem());
      flushMicrotasks();
      expect(api.removeItem).toHaveBeenCalledOnceWith('o-1', 'i-1');
      expect(component.order?.items).toEqual([]);
    }));

    it('applies a discount (AC-07)', () => {
      api.applyDiscount.and.returnValue(of(makeOrder({ discount: '10.00', total: '60.00', balance: '60.00' })));
      setup();
      component.applyDiscount('10.00');
      expect(api.applyDiscount).toHaveBeenCalledOnceWith('o-1', '10.00');
      expect(component.order?.total).toBe('60.00');
    });

    it('registers a payment and shows the new paid total (AC-12)', () => {
      api.registerPayment.and.returnValue(
        of(makeOrder({ payments: [makePayment()], paidTotal: '20.00', balance: '50.00', paymentStatus: 'PARTIAL' })),
      );
      const element = setup();
      const input = { amount: '20.00', paymentMethod: 'QR' as const, paymentDate: '2026-10-02', reference: 'ref-1' };
      component.registerPayment(input);
      fixture.detectChanges();
      expect(api.registerPayment).toHaveBeenCalledOnceWith('o-1', input);
      expect(text(element, 'paid')).toBe('Bs 20.00');
      expect(text(element, 'payment-panel')).toContain('Parcial');
      expect(toastr.success).toHaveBeenCalledWith('Pago registrado');
    });

    it('lets a delivered order with balance receive payments (AC-15)', () => {
      const element = setup(
        makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: [], canRegisterPayment: true }),
      );
      expect(element.querySelector('app-order-payments .card-header button')?.textContent).toContain('Registrar pago');
    });
  });
});

