import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, ParamMap, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { BehaviorSubject, Subject, of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { OrderApiError, OrderSummary } from '../../models/order';
import { CustomerOptionsService } from '../../services/customer-options.service';
import { OrdersApiService } from '../../services/orders-api.service';
import { makeSummary } from '../../testing/order-fixtures';
import { EMPTY_ALL, EMPTY_FILTERED, OrderListComponent } from './order-list.component';

function page(results: OrderSummary[], count = results.length): Page<OrderSummary> {
  return { count, next: null, previous: null, results };
}

describe('OrderListComponent', () => {
  let fixture: ComponentFixture<OrderListComponent>;
  let component: OrderListComponent;
  let api: jasmine.SpyObj<OrdersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;
  let queryParams: BehaviorSubject<ParamMap>;
  let customerOptions: jasmine.SpyObj<CustomerOptionsService>;

  const open = makeSummary({ id: 'a', code: 'P-AAAAAAAA' });
  const owing = makeSummary({
    id: 'b', code: 'P-BBBBBBBB', status: 'DELIVERED', paymentStatus: 'PARTIAL', total: '100.00', paidTotal: '40.00',
    balance: '60.00', customer: null, salesChannel: 'STORE', expectedDeliveryDate: null,
  });
  const cancelledNoPayments = makeSummary({
    id: 'c', code: 'P-CCCCCCCC', status: 'CANCELLED', paidTotal: '0.00', balance: '70.00',
  });
  const cancelledWithPayments = makeSummary({
    id: 'd', code: 'P-DDDDDDDD', status: 'CANCELLED', paymentStatus: 'PARTIAL', paidTotal: '20.00', balance: '50.00',
  });

  function params(values: Record<string, string> = {}): ParamMap {
    return convertToParamMap(values);
  }

  function lastListParams() {
    return api.list.calls.mostRecent().args[0];
  }

  /** Simula lo que hace el router tras un `navigate`: la URL cambia y la pantalla recibe los nuevos params. */
  function followNavigation(): void {
    const query = navigate.calls.mostRecent().args[1].queryParams as Record<string, string | null>;
    queryParams.next(
      convertToParamMap(Object.fromEntries(Object.entries(query).filter(([, value]) => value !== null)) as Record<string, string>),
    );
  }

  function start(initial: Record<string, string> = {}): HTMLElement {
    queryParams.next(params(initial));
    fixture = TestBed.createComponent(OrderListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['list']);
    api.list.and.returnValue(of(page([open, owing, cancelledNoPayments, cancelledWithPayments])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    customerOptions = jasmine.createSpyObj<CustomerOptionsService>('CustomerOptionsService', ['search']);
    customerOptions.search.and.returnValue(of([{ id: 'c-1', name: 'Ana Pérez' }]));
    queryParams = new BehaviorSubject<ParamMap>(params());

    TestBed.configureTestingModule({
      imports: [OrderListComponent],
      providers: [
        provideRouter([]),
        { provide: OrdersApiService, useValue: api },
        { provide: CustomerOptionsService, useValue: customerOptions },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { queryParamMap: queryParams } },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  it('loads the first page with no filters, newest first (AC-23)', () => {
    start();
    expect(api.list).toHaveBeenCalledOnceWith({ page: 1, pageSize: 10, ordering: '-order_date' });
    expect(component.currentShortcut).toBe('all');
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="ordering-help"]')?.textContent).toContain(
      'fecha de pedido, más recientes primero',
    );
  });

  it('links "+" to the new order form (AC-23)', () => {
    start();
    const link = fixture.debugElement.query(By.css('a[title="Nuevo pedido"]'));
    expect((link.nativeElement as HTMLAnchorElement).getAttribute('href')).toBe('/sales/orders/new');
  });

  describe('rows (AC-23)', () => {
    it('show date, code, customer, channel, expected date, total and a link to the detail', () => {
      const element = start();
      fixture.detectChanges();
      const text = element.textContent ?? '';
      expect(text).toContain('01/10/2026');
      expect(text).toContain('P-AAAAAAAA');
      expect(text).toContain('Ana Pérez');
      expect(text).toContain('WhatsApp');
      expect(text).toContain('05/10/2026');
      expect(text).toContain('Bs 70.00');
      const link = element.querySelector('a.fw-bold') as HTMLAnchorElement;
      expect(link.getAttribute('href')).toBe('/sales/orders/a');
      expect(component.total).toBe(4);
    });

    it('show "Sin cliente", "Venta directa" and a dash for a missing expected date', () => {
      const element = start();
      fixture.detectChanges();
      const text = element.textContent ?? '';
      expect(text).toContain('Sin cliente');
      expect(text).toContain('Venta directa');
      expect(text).toContain('—');
    });

    it('show the delivery and payment badges in separate columns (AC-23, REQ-SAL-016)', () => {
      const element = start();
      fixture.detectChanges();
      expect(element.querySelectorAll('app-order-status-badge i.fa-truck').length).toBe(4);
      expect(element.querySelectorAll('app-payment-status-badge i.fa-coins').length).toBe(4);
      const headers = Array.from(element.querySelectorAll('datatable-header-cell')).map((h) => h.textContent?.trim());
      expect(headers).toEqual(['Pedido', 'Cliente', 'Canal', 'Entrega prevista', 'Total', 'Saldo', 'Entrega', 'Pago', 'Acciones']);
    });

    it('highlight the balance of a delivered order that still owes money', () => {
      const element = start();
      fixture.detectChanges();
      const cells = Array.from(element.querySelectorAll('[data-testid="balance-cell"]')) as HTMLElement[];
      expect(cells[0].classList).toContain('text-danger');
      expect(cells[1].textContent?.trim()).toBe('Bs 60.00');
      expect(cells[1].classList).toContain('text-danger');
    });

    it('show a dash as balance for a cancelled order with no payments and a muted amount otherwise', () => {
      const element = start();
      fixture.detectChanges();
      const cells = Array.from(element.querySelectorAll('[data-testid="balance-cell"]')) as HTMLElement[];
      expect(cells[2].textContent?.trim()).toBe('—');
      expect(cells[2].classList).not.toContain('text-danger');
      expect(cells[3].textContent?.trim()).toBe('Bs 50.00');
      expect(cells[3].classList).not.toContain('text-danger');
    });

    it('show the right empty message depending on whether filters are active (AC-23)', () => {
      api.list.and.returnValue(of(page([])));
      start();
      expect(component.messages.emptyMessage).toBe(EMPTY_ALL);
      start({ status: 'CANCELLED' });
      expect(component.messages.emptyMessage).toBe(EMPTY_FILTERED);
    });
  });

  describe('shortcuts (AC-23)', () => {
    function click(shortcutId: string): void {
      const button = fixture.debugElement.query(By.css(`[data-shortcut="${shortcutId}"]`));
      (button.nativeElement as HTMLButtonElement).click();
    }

    it('offers the five shortcuts and marks the current one', () => {
      const element = start();
      const labels = Array.from(element.querySelectorAll('[data-testid="shortcuts"] button')).map((b) => b.textContent?.trim());
      expect(labels).toEqual(['Todos', 'Pendientes de entrega', 'Por cobrar', 'Entregados', 'Cancelados']);
      expect(element.querySelector('[data-shortcut="all"]')?.getAttribute('aria-pressed')).toBe('true');
      expect(element.querySelector('[data-shortcut="pending"]')?.getAttribute('aria-pressed')).toBe('false');
    });

    it('"Pendientes de entrega" only sets the fine filters and navigates with them in the URL', () => {
      start();
      click('pending');
      expect(component.filterForm.getRawValue().statusKey).toBe('PENDING_DELIVERY');
      expect(component.filterForm.getRawValue().paymentKey).toBe('ALL');
      expect(navigate).toHaveBeenCalledTimes(1);
      const call = navigate.calls.mostRecent().args;
      expect(call[0]).toEqual([]);
      expect(call[1].queryParams.status).toBe('PENDING_DELIVERY');
      expect(call[1].replaceUrl).toBeTrue();
    });

    it('reloads from the URL: pending deliveries come ordered by expected delivery', () => {
      start();
      click('pending');
      followNavigation();
      fixture.detectChanges();
      expect(lastListParams()).toEqual({
        page: 1, pageSize: 10, status: ['NEW', 'IN_PREPARATION', 'READY'], ordering: 'expected_delivery_date',
      });
      expect(component.currentShortcut).toBe('pending');
      expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="ordering-help"]')?.textContent).toContain(
        'entrega prevista, más próximas primero',
      );
    });

    it('"Por cobrar" asks for orders with a balance that are not cancelled', () => {
      start();
      click('receivable');
      followNavigation();
      expect(lastListParams()).toEqual({
        page: 1, pageSize: 10, status: ['NEW', 'IN_PREPARATION', 'READY', 'DELIVERED'], hasBalance: true,
        ordering: '-order_date',
      });
    });

    it('"Entregados" and "Cancelados" filter by one status', () => {
      start();
      click('delivered');
      followNavigation();
      expect(lastListParams()?.status).toEqual(['DELIVERED']);
      click('cancelled');
      followNavigation();
      expect(lastListParams()?.status).toEqual(['CANCELLED']);
    });

    it('"Todos" clears the delivery and payment filters', () => {
      start({ status: 'CANCELLED', pay: 'PAID' });
      click('all');
      expect(component.filterForm.getRawValue().statusKey).toBe('ALL');
      expect(component.filterForm.getRawValue().paymentKey).toBe('ALL');
    });
  });

  describe('fine filters (AC-23)', () => {
    it('restores the filters from the URL (they survive coming back from the detail)', () => {
      start({
        status: 'DELIVERED', pay: 'PARTIAL', channel: 'FAIR', customer: 'c-1', customer_name: 'Ana Pérez',
        date_field: 'expected_delivery_date', from: '2026-10-01', to: '2026-10-31', page: '2',
      });
      expect(component.filterForm.getRawValue()).toEqual({
        statusKey: 'DELIVERED', paymentKey: 'PARTIAL', channel: 'FAIR', customer: { id: 'c-1', name: 'Ana Pérez' },
        dateField: 'expected_delivery_date', dateFrom: '2026-10-01', dateTo: '2026-10-31',
      });
      expect(component.pageIndex).toBe(1);
      expect(lastListParams()).toEqual({
        page: 2, pageSize: 10, status: ['DELIVERED'], paymentStatus: ['PARTIAL'], salesChannel: 'FAIR',
        customerId: 'c-1', dateField: 'expected_delivery_date', dateFrom: '2026-10-01', dateTo: '2026-10-31',
        ordering: '-order_date',
      });
    });

    it('changing a filter goes back to page 1 and writes the URL', () => {
      start({ page: '3' });
      component.filterForm.patchValue({ channel: 'STORE' });
      expect(navigate.calls.mostRecent().args[1].queryParams).toEqual(
        jasmine.objectContaining({ channel: 'STORE', page: null }),
      );
    });

    it('offers the delivery, payment and channel options of the design', () => {
      const element = start();
      const options = (id: string) =>
        Array.from(element.querySelectorAll(`#${id} option`)).map((o) => o.textContent?.trim());
      expect(options('filter-status')).toEqual([
        'Todos', 'Pendientes de entrega', 'Nuevo', 'En preparación', 'Listo', 'Entregado', 'Cancelado', 'No cancelados',
      ]);
      expect(options('filter-payment')).toEqual(['Todos', 'Pendiente', 'Parcial', 'Pagado', 'Reembolsado', 'Con saldo pendiente']);
      expect(options('filter-channel')).toEqual(['Todos', 'WhatsApp', 'Facebook', 'Instagram', 'Venta directa', 'Feria', 'Otro']);
      expect(options('filter-date-field')).toEqual(['Pedido', 'Entrega prevista']);
    });

    it('"Limpiar filtros" resets everything and is disabled when nothing is filtered', () => {
      const element = start();
      const clear = Array.from(element.querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Limpiar filtros');
      expect(clear?.disabled).toBeTrue();
      queryParams.next(params({ status: 'CANCELLED', channel: 'FAIR' }));
      fixture.detectChanges();
      expect(clear?.disabled).toBeFalse();
      clear?.click();
      expect(component.filterForm.getRawValue()).toEqual({
        statusKey: 'ALL', paymentKey: 'ALL', channel: '', customer: null, dateField: 'order_date', dateFrom: '', dateTo: '',
      });
    });
  });

  it('keeps searching customers after an option is chosen and ng-select emits null (EDGE-14, REV-02)', fakeAsync(() => {
    start();
    customerOptions.search.calls.reset();
    component.customerInput$.next(null as unknown as string);
    tick(300);
    expect(customerOptions.search).toHaveBeenCalledTimes(1);
    expect(component.customersLoading).toBeFalse();
    component.customerInput$.next('zzz');
    tick(300);
    expect(customerOptions.search.calls.mostRecent().args[0]).toBe('zzz');
    expect(component.customersLoading).toBeFalse();
  }));

  describe('paging and errors', () => {
    it('navigates to the requested page and ignores the initial page event (AC-23)', () => {
      start();
      component.onPage({ offset: 0 });
      expect(navigate).not.toHaveBeenCalled();
      component.onPage({ offset: 2 });
      expect(navigate.calls.mostRecent().args[1].queryParams.page).toBe('3');
      followNavigation();
      expect(lastListParams()?.page).toBe(3);
    });

    it('shows the loading state while the request is in flight', () => {
      const pending = new Subject<Page<OrderSummary>>();
      api.list.and.returnValue(pending);
      start();
      expect(component.loading).toBeTrue();
      pending.next(page([open]));
      pending.complete();
      expect(component.loading).toBeFalse();
      expect(component.rows).toEqual([open]);
    });

    it('shows a toast when the list cannot be loaded', () => {
      api.list.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
      start();
      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
      expect(component.loading).toBeFalse();
      expect(component.rows).toEqual([]);
    });
  });
});
