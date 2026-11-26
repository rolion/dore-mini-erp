import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed, fakeAsync, flushMicrotasks } from '@angular/core/testing';
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { BehaviorSubject, Subject, of, throwError } from 'rxjs';
import { NO_SALES_DEFAULTS, SalesSettingsService } from '../../services/sales-settings.service';
import Swal, { SweetAlertResult } from 'sweetalert2';

import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../../products';
import { DeliveryPreview, FieldErrors, Order, OrderApiError, OrderItem, OrderRuleError } from '../../models/order';
import { ReturnDialogComponent } from '../../components/return-dialog/return-dialog.component';
import { ModulesService } from '../../../../core/service/modules.service';
import { OrdersApiService } from '../../services/orders-api.service';
import { NO_STOCK_PREVIEW, makeItem, makeOrder, makePayment, makePreview, makeReturnPreview } from '../../testing/order-fixtures';
import { OrderDetailComponent } from './order-detail.component';

interface DialogHooks {
  askDeliveryDate(order: Order): Promise<string | null>;
  askCancelReason(order: Order): Promise<string | null>;
  confirmRemove(item: OrderItem): Promise<boolean>;
  confirmRefund(order: Order): Promise<boolean>;
  deliverWithStock(order: Order, preview: DeliveryPreview): Promise<void>;
}

const EMPTY_PRODUCTS: Page<never> = { count: 0, next: null, previous: null, results: [] };

describe('OrderDetailComponent', () => {
  let fixture: ComponentFixture<OrderDetailComponent>;
  let component: OrderDetailComponent;
  let api: jasmine.SpyObj<OrdersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;
  let navigate: jasmine.Spy;
  let params$: BehaviorSubject<ParamMap>;

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
      'applyDiscount', 'registerPayment', 'deliveryPreview', 'returnPreview',
    ]);
    api.deliveryPreview.and.returnValue(of(NO_STOCK_PREVIEW));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    params$ = new BehaviorSubject<ParamMap>(convertToParamMap({ id: 'o-1' }));
    const products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    products.list.and.returnValue(of(EMPTY_PRODUCTS));

    TestBed.configureTestingModule({
      imports: [OrderDetailComponent],
      providers: [...provideTestTranslations(), 
        provideRouter([]),
        { provide: OrdersApiService, useValue: api },
        { provide: ProductsApiService, useValue: products },
        { provide: ToastrService, useValue: toastr },
        { provide: ModulesService, useValue: { enabledKeysValue: new Set(['sales', 'accounting']) } },
        { provide: ActivatedRoute, useValue: { paramMap: params$.asObservable() } },
        { provide: SalesSettingsService, useValue: { defaults: () => of(NO_SALES_DEFAULTS) } },
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

    it('loads the new order when only the id in the route changes, dropping the previous one (AC-17, AC-25)', () => {
      const other = makeOrder({ id: 'o-2', code: 'P-22222222', notes: 'Otro pedido' });
      setup();
      component.fieldErrors = { discount: ['viejo'] };
      api.get.and.returnValue(of(other));
      params$.next(convertToParamMap({ id: 'o-2' }));
      fixture.detectChanges();
      expect(api.get).toHaveBeenCalledWith('o-2');
      expect(component.order?.id).toBe('o-2');
      expect(component.fieldErrors).toEqual({});
      expect(text(fixture.nativeElement as HTMLElement, 'order-code')).toBe('Pedido P-22222222');
    });

    it('acts on the order of the current route after the id changed (AC-25)', () => {
      api.prepare.and.returnValue(of(makeOrder({ id: 'o-2', status: 'IN_PREPARATION' })));
      setup();
      api.get.and.returnValue(of(makeOrder({ id: 'o-2' })));
      params$.next(convertToParamMap({ id: 'o-2' }));
      component.runPrimary();
      expect(api.prepare).toHaveBeenCalledOnceWith('o-2');
    });

    it('ignores the answer of a previous order that arrives late (AC-17)', () => {
      const first = new Subject<Order>();
      api.get.and.returnValue(first);
      fixture = TestBed.createComponent(OrderDetailComponent);
      component = fixture.componentInstance;
      fixture.detectChanges();
      api.get.and.returnValue(of(makeOrder({ id: 'o-2' })));
      params$.next(convertToParamMap({ id: 'o-2' }));
      first.next(makeOrder({ id: 'o-1' }));
      fixture.detectChanges();
      expect(component.order?.id).toBe('o-2');
    });

    it('warns and goes back to the list when the order does not exist (EDGE-12)', () => {
      api.get.and.returnValue(throwError(() => new OrderApiError('Pedido no encontrado.', 404)));
      fixture = TestBed.createComponent(OrderDetailComponent);
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledWith('Pedido no encontrado.');
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/sales/orders']);
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

    it('shows the order warehouse in the delivery panel only when it has one (AC-07)', () => {
      const withWarehouse = setup(makeOrder({ warehouse: { id: 'w-1', name: 'Central' } }));
      expect(text(q(withWarehouse, 'delivery-panel') as HTMLElement, 'warehouse')).toBe('Central');
    });

    it('hides the warehouse row when the order has none (AC-07)', () => {
      const element = setup(makeOrder({ warehouse: null }));
      expect(q(q(element, 'delivery-panel') as HTMLElement, 'warehouse')).toBeNull();
    });

    it('shows "Sin saldo" when nothing is owed and the real delivery date once delivered', () => {
      const element = setup(
        makeOrder({
          status: 'DELIVERED', editable: false, allowedTransitions: [], paymentStatus: 'PAID', paidTotal: '70.00',
          balance: '0.00', deliveredDate: '2026-10-06',
        }),
      );
      expect(text(element, 'delivered-date')).toBe('06/10/2026');
      expect(element.textContent).toContain('Pagado');
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

  describe('refined layout (TASK-refinar-ux-pedidos-ventas)', () => {
    it('orders items, amounts and payments before the order data, with creation dates as a footnote (AC-01)', () => {
      const element = setup();
      const items = element.querySelector('app-order-items') as HTMLElement;
      const summary = element.querySelector('app-order-summary') as HTMLElement;
      const payments = element.querySelector('app-order-payments') as HTMLElement;
      const customer = q(element, 'customer') as HTMLElement;
      const follows = (a: HTMLElement, b: HTMLElement) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING);
      expect(follows(q(element, 'payment-panel') as HTMLElement, items)).toBeTrue();
      expect(follows(items, summary)).toBeTrue();
      expect(follows(summary, payments)).toBeTrue();
      expect(follows(payments, customer)).toBeTrue();
      expect(text(element, 'audit')).toContain('Creado 01/10/2026');
      expect(text(element, 'audit')).toContain('Última actualización 01/10/2026');
    });

    it('registers a payment from the Cobro card by opening the payment form (AC-02)', () => {
      const element = setup();
      expect(element.querySelector('#payment-amount')).toBeNull();
      (q(element, 'pay-action') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(element.querySelector('#payment-amount')).not.toBeNull();
    });

    it('does not offer to register a payment when nothing can be collected (AC-02)', () => {
      const element = setup(makeOrder({ canRegisterPayment: false, balance: '0.00', paymentStatus: 'PAID', paidTotal: '70.00' }));
      expect(q(element, 'pay-action')).toBeNull();
    });

    it('says "Sin productos" instead of a green "Sin saldo" for an order without lines (AC-03)', () => {
      const element = setup(makeOrder({
        items: [], subtotal: '0.00', total: '0.00', balance: '0.00', canRegisterPayment: false,
      }));
      expect(text(element, 'balance-panel')).toBe('Sin productos');
      expect(q(element, 'balance-panel')?.classList).not.toContain('text-success');
      expect(q(element, 'pay-action')).toBeNull();
    });

    it('keeps the green "Sin saldo" for a paid order with products (AC-03)', () => {
      const element = setup(makeOrder({ balance: '0.00', paymentStatus: 'PAID', paidTotal: '70.00', canRegisterPayment: false }));
      expect(text(element, 'balance-panel')).toBe('Sin saldo');
      expect(q(element, 'balance-panel')?.classList).toContain('text-success');
    });

    it('keeps one solid primary action and makes the other actions outline (AC-04)', () => {
      const element = setup();
      expect(q(element, 'primary-action')?.classList).toContain('btn-primary');
      expect(q(element, 'edit-link')?.classList).toContain('btn-outline-primary');
      expect(element.querySelector('app-order-summary button')?.classList).toContain('btn-outline-primary');
    });

    it('formats the payment date as dd/MM/yyyy (AC-05)', () => {
      const element = setup(makeOrder({ payments: [makePayment({ paymentDate: '2026-11-04' })] }));
      expect(text(element, 'payment-row')).toContain('04/11/2026');
    });
  });

  describe('data and amounts', () => {
    it('shows customer (linked), channel label, dates and notes (AC-17)', () => {
      const element = setup(makeOrder({ salesChannel: 'STORE', notes: 'Sin picante' }));
      expect(q(element, 'customer')?.querySelector('a')?.getAttribute('href')).toBe('/pocketbiz/customers/c-1');
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
      expect(q(editable, 'edit-link')?.getAttribute('href')).toBe('/pocketbiz/sales/orders/o-1/edit');
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

    it('opens the stock dialog instead of the date prompt when the order has controlled items (UI-01, AC-14)', fakeAsync(() => {
      const preview = makePreview();
      api.deliveryPreview.and.returnValue(of(preview));
      setup(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      const ask = spyOn(dialogs(), 'askDeliveryDate');
      const withStock = spyOn(dialogs(), 'deliverWithStock').and.resolveTo();
      component.runPrimary();
      flushMicrotasks();
      expect(api.deliveryPreview).toHaveBeenCalledOnceWith('o-1');
      expect(withStock).toHaveBeenCalledOnceWith(jasmine.objectContaining({ id: 'o-1' }), preview);
      expect(ask).not.toHaveBeenCalled();
      expect(api.deliver).not.toHaveBeenCalled();
    }));

    it('uses the usual confirmation without asking for a warehouse when nothing controls stock (UI-01, AC-08)', fakeAsync(() => {
      api.deliver.and.returnValue(of(makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: [] })));
      setup(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      spyOn(dialogs(), 'askDeliveryDate').and.resolveTo('2026-10-03');
      const withStock = spyOn(dialogs(), 'deliverWithStock');
      component.runPrimary();
      flushMicrotasks();
      expect(withStock).not.toHaveBeenCalled();
      expect(api.deliver).toHaveBeenCalledOnceWith('o-1', '2026-10-03');
    }));

    it('reports a preview failure and reloads the order on a rule conflict', fakeAsync(() => {
      api.deliveryPreview.and.returnValue(throwError(() => new OrderRuleError('Esa acción no está permitida.', 'invalid_transition')));
      setup(makeOrder({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      component.runPrimary();
      flushMicrotasks();
      expect(toastr.error).toHaveBeenCalledWith('Esa acción no está permitida.');
      expect(api.get).toHaveBeenCalledTimes(2);
      expect(component.busy).toBeFalse();
    }));

    it('shows the stock output card only for an order that generated one (UI-05)', () => {
      const element = setup(makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: [] }));
      expect(q(element, 'stock-output-card')).toBeNull();
      const withOutput = makeOrder({
        status: 'DELIVERED', editable: false, allowedTransitions: [],
        stockOutput: {
          reference: 'P-1A2B3C4D', warehouseId: 'w-1', warehouseName: 'Central', occurredAt: '2026-10-03T15:30:00Z',
          userName: 'ana', movements: [{ id: 'm-1', productId: 'p-1', productName: 'Bolsas', quantity: '4.0000', unit: 'u' }],
        },
      });
      component.order = withOutput;
      fixture.detectChanges();
      expect(text(element, 'output-warehouse')).toBe('Central');
      expect(element.querySelector('app-order-status-badge')?.textContent).toContain('Entregado');
    });

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
      expect(api.cancel).toHaveBeenCalledOnceWith('o-1', 'No lo quiere', false);
      expect(q(element, 'alert-cancelled')).not.toBeNull();
    }));

    it('asks to confirm the external refund when the order has payments and sends it (AC-02)', fakeAsync(() => {
      api.cancel.and.returnValue(of(makeOrder({ status: 'CANCELLED', allowedTransitions: [], refundAcknowledged: true })));
      setup(makeOrder({ payments: [makePayment()], paidTotal: '20.00' }));
      spyOn(dialogs(), 'askCancelReason').and.resolveTo('No lo quiere');
      const refund = spyOn(dialogs(), 'confirmRefund').and.resolveTo(true);
      void component.cancel();
      flushMicrotasks();
      expect(refund).toHaveBeenCalledTimes(1);
      expect(api.cancel).toHaveBeenCalledOnceWith('o-1', 'No lo quiere', true);
    }));

    it('does not cancel when the refund is not confirmed (AC-02)', fakeAsync(() => {
      setup(makeOrder({ payments: [makePayment()], paidTotal: '20.00' }));
      spyOn(dialogs(), 'askCancelReason').and.resolveTo('No lo quiere');
      spyOn(dialogs(), 'confirmRefund').and.resolveTo(false);
      void component.cancel();
      flushMicrotasks();
      expect(api.cancel).not.toHaveBeenCalled();
    }));

    describe('return (AC-03, AC-09, AC-11)', () => {
      const delivered = () => makeOrder({ status: 'DELIVERED', editable: false, allowedTransitions: ['return'] });

      it('offers «Registrar devolución» only when the server allows it', () => {
        expect(q(setup(delivered()), 'return-action')).not.toBeNull();
        expect(q(setup(makeOrder({ status: 'DELIVERED', allowedTransitions: [] })), 'return-action')).toBeNull();
      });

      it('reads the preview, opens the dialog and shows the returned order', fakeAsync(() => {
        const returned = makeOrder({ status: 'RETURNED', allowedTransitions: [], returnReason: 'Defectuoso', returnedByName: 'ana' });
        const preview = makeReturnPreview();
        api.returnPreview.and.returnValue(of(preview));
        const element = setup(delivered());
        const init = jasmine.createSpy('init');
        const ref = { componentInstance: { init }, result: Promise.resolve(returned) } as unknown as NgbModalRef;
        const open = spyOn(TestBed.inject(NgbModal), 'open').and.returnValue(ref);
        (q(element, 'return-action') as HTMLButtonElement).click();
        flushMicrotasks();
        fixture.detectChanges();
        expect(api.returnPreview).toHaveBeenCalledOnceWith('o-1');
        expect(open.calls.mostRecent().args[0]).toBe(ReturnDialogComponent);
        expect(init).toHaveBeenCalledOnceWith(jasmine.objectContaining({ id: 'o-1' }), preview);
        expect(component.order?.status).toBe('RETURNED');
        expect(toastr.success).toHaveBeenCalledWith('Pedido devuelto.');
        expect(text(element, 'reversal-reason')).toBe('Defectuoso');
        expect(q(element, 'return-action')).toBeNull();
      }));

      it('keeps the order when the dialog is dismissed', fakeAsync(() => {
        api.returnPreview.and.returnValue(of(makeReturnPreview()));
        setup(delivered());
        const ref = { componentInstance: { init: () => undefined }, result: Promise.reject('x') } as unknown as NgbModalRef;
        spyOn(TestBed.inject(NgbModal), 'open').and.returnValue(ref);
        void component.registerReturn();
        flushMicrotasks();
        expect(component.order?.status).toBe('DELIVERED');
        expect(toastr.error).not.toHaveBeenCalled();
      }));

      it('shows the server message when the preview fails', fakeAsync(() => {
        api.returnPreview.and.returnValue(throwError(() => new OrderApiError('Falló', 500)));
        setup(delivered());
        void component.registerReturn();
        flushMicrotasks();
        expect(toastr.error).toHaveBeenCalledWith('Falló');
      }));
    });

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

  describe('fiscal period (AC-13)', () => {
    it('shows the numbered code and its period under the title (UI-02)', () => {
      const element = setup(makeOrder({
        code: 'NV-000007', status: 'IN_PREPARATION', fiscalPeriod: { id: 'fp-1', name: 'Gestión 2026' },
      }));
      expect(text(element, 'order-code')).toBe('Pedido NV-000007');
      expect(text(element, 'order-period')).toBe('Período fiscal: Gestión 2026');
    });

    it('shows no period for an order that is not confirmed yet (UI-02)', () => {
      expect(q(setup(), 'order-period')).toBeNull();
    });

    it('explains a fiscal period block on confirming, with the link to Accounting (UI-03)', () => {
      api.prepare.and.returnValue(throwError(() => new OrderRuleError('x', 'fiscal_period_missing')));
      const element = setup();
      component.runPrimary();
      fixture.detectChanges();
      expect(text(element, 'fiscal-period-message')).toContain('ningún período fiscal');
      expect(q(element, 'fiscal-period-link')).not.toBeNull();
      expect(toastr.error).not.toHaveBeenCalled();
    });

    it('clears the block when the next action starts (UI-03)', () => {
      api.prepare.and.returnValues(throwError(() => new OrderRuleError('x', 'fiscal_period_closed')), of(makeOrder({ status: 'IN_PREPARATION' })));
      const element = setup();
      component.runPrimary();
      fixture.detectChanges();
      expect(q(element, 'alert-fiscal-period')).not.toBeNull();
      component.runPrimary();
      fixture.detectChanges();
      expect(q(element, 'alert-fiscal-period')).toBeNull();
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

    it('explains missing accounting configuration of a payment in an alert with a link, without a toast (409, VEN-01)', () => {
      const issues = [{ code: 'role_unconfigured', subject: 'Anticipos de clientes', message: 'Falta configurar la cuenta «Anticipos de clientes».' }];
      api.registerPayment.and.returnValue(throwError(() => new OrderRuleError('Falta configurar.', 'posting_configuration_missing', [], '', issues)));
      const element = setup();
      component.registerPayment({ amount: '10.00', paymentMethod: 'CASH', paymentDate: '2026-10-01', reference: '', idempotencyKey: 'k-1' });
      fixture.detectChanges();
      expect(toastr.error).not.toHaveBeenCalled();
      expect(text(element, 'alert-posting-issues')).toContain('Falta configurar la cuenta «Anticipos de clientes».');
      const link = element.querySelector('[data-testid="link-posting-settings"]');
      expect(link?.getAttribute('href')).toContain('/sales/settings');
      expect(link?.getAttribute('href')).toContain('tab=posting');
    });

    it('clears the accounting alert when the next action starts', () => {
      const issues = [{ code: 'role_unconfigured', subject: 'x', message: 'Falta algo.' }];
      api.registerPayment.and.returnValue(throwError(() => new OrderRuleError('Falta.', 'posting_configuration_missing', [], '', issues)));
      setup();
      component.registerPayment({ amount: '10.00', paymentMethod: 'CASH', paymentDate: '2026-10-01', reference: '', idempotencyKey: 'k-1' });
      expect(component.postingIssues.length).toBe(1);
      api.applyDiscount.and.returnValue(of(makeOrder()));
      component.applyDiscount('1.00');
      expect(component.postingIssues).toEqual([]);
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
      const input = { amount: '20.00', paymentMethod: 'QR' as const, paymentDate: '2026-10-02', reference: 'ref-1', idempotencyKey: 'k-1' };
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
      expect(text(element, 'pay-action')).toContain('Registrar pago');
    });
  });

  describe('detail of an order in progress (AC-11..AC-15, DDR detalle en curso)', () => {
    const inPreparation = (overrides: Partial<Order> = {}): Order =>
      makeOrder({
        status: 'IN_PREPARATION', paymentStatus: 'PARTIAL', paidTotal: '20.00', balance: '50.00',
        allowedTransitions: ['ready', 'cancel'], canRegisterPayment: true, discount: '5.00', total: '65.00',
        warehouse: { id: 'w-1', name: 'Central' }, payments: [makePayment()], ...overrides,
      });

    it('shows code, state badge and payment badge in the header with the actions on the right (AC-11)', () => {
      const element = setup(inPreparation());
      expect(text(element, 'order-code')).toContain('P-1A2B3C4D');
      expect(element.querySelector('app-order-status-badge')?.textContent).toContain('En preparación');
      expect(element.querySelector('app-payment-status-badge')?.textContent).toContain('Parcial');
      expect(text(element, 'primary-action')).toBe('Marcar listo');
      expect(text(element, 'pay-action')).toBe('Registrar pago');
    });

    it('shows customer, channel, dates and warehouse read-only (AC-14)', () => {
      const element = setup(inPreparation());
      expect(text(element, 'customer')).toBe('Ana Pérez');
      expect(text(element, 'channel')).toBeTruthy();
      expect(text(element, 'order-date')).toBe('01/10/2026');
      expect(text(element, 'expected-date')).toBe('05/10/2026');
      expect(text(element, 'warehouse')).toBe('Central');
      expect(element.querySelector('input, select, textarea')).toBeNull();
    });

    it('lists the products, the amounts and the payments without edit controls (AC-14)', () => {
      const element = setup(inPreparation());
      expect(element.querySelectorAll('[data-testid="item-row"]').length).toBe(1);
      expect(text(element, 'subtotal')).toContain('70.00');
      expect(text(element, 'discount')).toContain('5.00');
      expect(text(element, 'total')).toContain('65.00');
      expect(text(element, 'paid')).toContain('20.00');
      expect(text(element, 'balance')).toContain('50.00');
      expect(element.querySelectorAll('[data-testid="payment-row"]').length).toBe(1);
      expect(element.querySelector('[data-testid="edit-link"]')).toBeNull();
      expect(element.querySelector('app-order-items')).toBeNull();
    });

    it('marks the order ready and updates the state on screen (AC-12)', () => {
      const element = setup(inPreparation());
      api.ready.and.returnValue(of(inPreparation({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] })));
      (q(element, 'primary-action') as HTMLButtonElement).click();
      fixture.detectChanges();
      expect(api.ready).toHaveBeenCalledOnceWith('o-1');
      expect(element.querySelector('app-order-status-badge')?.textContent).toContain('Listo');
      expect(text(element, 'primary-action')).toBe('Marcar entregado');
    });

    it('offers the delivery in READY and no primary action once delivered (AC-12)', () => {
      const ready = setup(inPreparation({ status: 'READY', allowedTransitions: ['deliver', 'cancel'] }));
      expect(text(ready, 'primary-action')).toBe('Marcar entregado');
      const delivered = setup(inPreparation({ status: 'DELIVERED', editable: false, allowedTransitions: [], deliveredDate: '2026-10-06' }));
      expect(q(delivered, 'primary-action')).toBeNull();
      expect(text(delivered, 'delivered-date')).toBe('06/10/2026');
    });

    it('hides the payment button when the server does not allow collecting (AC-13)', () => {
      const element = setup(inPreparation({ canRegisterPayment: false, balance: '0.00', paymentStatus: 'PAID', paidTotal: '65.00' }));
      expect(q(element, 'pay-action')).toBeNull();
    });

    it('opens the payment modal and shows the updated order afterwards (AC-13)', fakeAsync(() => {
      const element = setup(inPreparation());
      const init = jasmine.createSpy('init');
      const updated = inPreparation({ paymentStatus: 'PAID', paidTotal: '65.00', balance: '0.00', canRegisterPayment: false });
      const open = spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({
        componentInstance: { init }, result: Promise.resolve(updated),
      } as unknown as NgbModalRef);
      (q(element, 'pay-action') as HTMLButtonElement).click();
      flushMicrotasks();
      fixture.detectChanges();
      expect(open).toHaveBeenCalled();
      expect(init).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'o-1' }));
      expect(toastr.success).toHaveBeenCalled();
      expect(element.querySelector('app-payment-status-badge')?.textContent).toContain('Pagado');
      expect(q(element, 'pay-action')).toBeNull();
    }));

    it('shows the balance in a green line when nothing is owed (REV-10)', () => {
      const element = setup(inPreparation({ paymentStatus: 'PAID', paidTotal: '65.00', balance: '0.00', canRegisterPayment: false }));
      expect(text(element, 'balance')).toContain('0.00');
      expect(q(element, 'balance')?.classList).toContain('text-success');
      const owed = setup(inPreparation());
      expect(q(owed, 'balance')?.classList).toContain('text-danger');
    });

    it('warns and reloads the order when the payment modal is dismissed because the order changed (REV-11)', fakeAsync(() => {
      const element = setup(inPreparation());
      spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({
        componentInstance: { init: () => undefined }, result: Promise.reject('stale'),
      } as unknown as NgbModalRef);
      api.get.calls.reset();
      api.get.and.returnValue(of(inPreparation({ paidTotal: '65.00', balance: '0.00', paymentStatus: 'PAID', canRegisterPayment: false })));
      (q(element, 'pay-action') as HTMLButtonElement).click();
      flushMicrotasks();
      fixture.detectChanges();
      expect(toastr.error).toHaveBeenCalledTimes(1);
      expect(api.get).toHaveBeenCalledOnceWith('o-1');
      expect(text(element, 'paid')).toContain('65.00');
      expect(toastr.success).not.toHaveBeenCalled();
    }));

    it('keeps the order untouched when the payment modal is dismissed (AC-13)', fakeAsync(() => {
      const element = setup(inPreparation());
      spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({
        componentInstance: { init: () => undefined }, result: Promise.reject('closed'),
      } as unknown as NgbModalRef);
      (q(element, 'pay-action') as HTMLButtonElement).click();
      flushMicrotasks();
      expect(toastr.success).not.toHaveBeenCalled();
      expect(component.order?.paidTotal).toBe('20.00');
    }));

    it('keeps the current detail for NEW orders and uses the compact view for cancelled ones (AC-15, AC-09)', () => {
      const created = setup(makeOrder());
      expect(created.querySelector('app-order-items')).not.toBeNull();
      expect(q(created, 'delivery-panel')).not.toBeNull();
      const cancelled = setup(makeOrder({ status: 'CANCELLED', editable: false, allowedTransitions: [], cancellationReason: 'x' }));
      expect(q(cancelled, 'alert-cancelled')).not.toBeNull();
      expect(q(cancelled, 'order-data')).not.toBeNull();
      expect(q(cancelled, 'delivery-panel')).toBeNull();
      expect(cancelled.querySelector('app-order-items')).toBeNull();
    });

    it('shows a refunded cancellation as refunded, not as a settled sale (AC-02, AC-09)', () => {
      const element = setup(makeOrder({
        status: 'CANCELLED', editable: false, allowedTransitions: [], canRegisterPayment: false,
        cancellationReason: 'Sin stock', payments: [makePayment({ amount: '28.00' })], paidTotal: '28.00',
        balance: '42.00', paymentStatus: 'REFUNDED', refundAcknowledged: true, cancelledByName: 'ana',
        cancelledAt: '2026-10-04T10:00:00Z',
      }));
      expect(text(element, 'refund-registered')).toContain('reembolso quedó registrado');
      expect(text(element, 'alert-cancelled')).not.toContain('Los pagos registrados se conservan');
      expect(text(element, 'paid')).toContain('28.00');
      expect(q(element, 'balance')).toBeNull();
      expect(element.textContent).toContain('Reembolsado');
      expect(q(element, 'reversal-card')).not.toBeNull();
    });
  });
});

