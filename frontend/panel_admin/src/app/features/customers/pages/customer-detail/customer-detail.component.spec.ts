import { provideTestTranslations } from '../../../../core/i18n/testing';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { of, throwError } from 'rxjs';

import { ModulesService } from '../../../../core/service/modules.service';
import { Customer, CustomerApiError, CustomerOrderSummary } from '../../models/customer';
import { CustomerOrdersApiService } from '../../services/customer-orders-api.service';
import { CustomersApiService } from '../../services/customers-api.service';
import { makeCustomer } from '../../testing/customer-fixtures';
import { CustomerDetailComponent } from './customer-detail.component';

interface ToggleHook {
  confirmToggle(customer: Customer): Promise<boolean>;
}

const modulesState = { salesDisabled: false };
const modulesFake = { isDisabled: (key: string) => key === 'sales' && modulesState.salesDisabled };

function makeOrder(overrides: Partial<CustomerOrderSummary> = {}): CustomerOrderSummary {
  return {
    id: 'o1', code: 'A-0042', date: '2026-10-05', total: '120.50', paidTotal: '100.00', balance: '20.50',
    status: 'DELIVERED', paymentStatus: 'PARTIAL', ...overrides,
  };
}

describe('CustomerDetailComponent', () => {
  let api: jasmine.SpyObj<CustomersApiService>;
  let ordersApi: jasmine.SpyObj<CustomerOrdersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['get', 'activate', 'deactivate']);
    ordersApi = jasmine.createSpyObj<CustomerOrdersApiService>('CustomerOrdersApiService', ['list']);
    ordersApi.list.and.returnValue(of({ orders: [], total: 0 }));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), 
        provideRouter([{ path: 'pocketbiz/customers/:id', component: CustomerDetailComponent }]),
        { provide: CustomersApiService, useValue: api },
        { provide: CustomerOrdersApiService, useValue: ordersApi },
        { provide: ModulesService, useValue: modulesFake },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  afterEach(() => (modulesState.salesDisabled = false));

  async function open(id = 'c-1') {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(`/pocketbiz/customers/${id}`, CustomerDetailComponent);
    harness.detectChanges();
    return { component, el: harness.routeNativeElement as HTMLElement, harness };
  }

  it('shows every field of the customer with its state, and the actions (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { el } = await open();

    expect(api.get).toHaveBeenCalledOnceWith('c-1');
    const text = el.textContent ?? '';
    for (const expected of ['Ana Pérez', '+59176543210', 'ana@example.com', 'Cliente frecuente', 'Activo']) {
      expect(text).toContain(expected);
    }
    const actions = el.querySelector('[data-testid="customer-actions"]') as HTMLElement;
    expect(actions.closest('.card-header')).not.toBeNull();
    const newOrder = actions.querySelector('a.btn-primary') as HTMLAnchorElement;
    expect(newOrder.textContent?.trim()).toBe('Nuevo pedido');
    expect(newOrder.getAttribute('href')).toBe('/pocketbiz/sales/orders/new?customer=c-1&customer_name=Ana%20P%C3%A9rez');
    const editLink = actions.querySelector('a.btn-light') as HTMLAnchorElement;
    expect(editLink.textContent?.trim()).toBe('Editar');
    expect(editLink.getAttribute('href')).toBe('/pocketbiz/customers/c-1/edit');
    expect(actions.querySelector('button.btn-warning')?.textContent?.trim()).toBe('Desactivar');
    expect(el.textContent).not.toContain('Volver');
    expect(Array.from(el.querySelectorAll('dt')).map((dt) => dt.textContent?.trim())).toEqual(['Teléfono', 'Correo', 'Notas']);
  });

  it('makes the phone and the email actionable (AC-02)', async () => {
    api.get.and.returnValue(of(makeCustomer({ phone: '+591 7654-3210' })));
    const { el } = await open();
    expect(el.querySelector('a[href="tel:+591 7654-3210"]')).not.toBeNull();
    expect(el.querySelector('a[href="mailto:ana@example.com"]')).not.toBeNull();
    const whatsapp = el.querySelector('[data-testid="whatsapp"]') as HTMLAnchorElement;
    expect(whatsapp.getAttribute('href')).toBe('https://wa.me/59176543210');
    expect(whatsapp.getAttribute('target')).toBe('_blank');
    expect(whatsapp.getAttribute('rel')).toBe('noopener');
    expect(whatsapp.getAttribute('aria-label')).toBe('Escribir por WhatsApp a Ana Pérez');
  });

  it('says "Sin teléfono", "Sin correo" and "Sin notas" for empty optional fields (AC-02)', async () => {
    api.get.and.returnValue(of(makeCustomer({ phone: '', email: '', notes: '' })));
    const { el } = await open();
    expect(el.textContent).toContain('Sin teléfono');
    expect(el.textContent).toContain('Sin correo');
    expect(el.textContent).toContain('Sin notas');
    expect(el.querySelector('[data-testid="whatsapp"]')).toBeNull();
    expect(el.querySelector('a[href^="tel:"]')).toBeNull();
  });

  it('shows the creation and update dates as a discreet footer (AC-08)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { el } = await open();
    const audit = el.querySelector('[data-testid="audit"]') as HTMLElement;
    expect(audit.textContent).toContain('Creado');
    expect(audit.textContent).toContain('Última actualización');
    expect(Array.from(el.querySelectorAll('dt')).map((dt) => dt.textContent?.trim())).not.toContain('Creado');
  });

  it('shows last purchase, orders, total purchased and outstanding balance of the loaded orders (AC-03)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(
      of({
        total: 3,
        orders: [
          makeOrder({ id: 'o3', date: '2026-10-30', total: '0.10', balance: '0.00' }),
          makeOrder({ id: 'o2', date: '2026-10-05', total: '120.50', balance: '20.50' }),
          makeOrder({ id: 'o1', date: '2026-10-31', total: '999.00', balance: '999.00', status: 'CANCELLED' }),
        ],
      }),
    );
    const { el } = await open();
    const text = (id: string) => el.querySelector(`[data-testid="${id}"]`)?.textContent?.trim();
    expect(text('summary-last')).toBe('30/10/2026');
    expect(text('summary-count')).toBe('2');
    expect(text('summary-total')).toBe('Bs 120.60');
    expect(text('summary-balance')).toBe('Bs 20.50');
    expect(el.querySelector('[data-testid="summary-balance"]')?.classList).toContain('text-danger');
    expect(el.textContent).toContain('Pendiente de cobro');
    expect(el.querySelector('[data-testid="summary-partial"]')).toBeNull();
  });

  it('shows "Sin compras" and zero amounts for a customer without orders (AC-03)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { el } = await open();
    const text = (id: string) => el.querySelector(`[data-testid="${id}"]`)?.textContent?.trim();
    expect(text('summary-last')).toBe('Sin compras');
    expect(text('summary-count')).toBe('0');
    expect(text('summary-total')).toBe('Bs 0.00');
    expect(text('summary-balance')).toBe('Bs 0.00');
    expect(el.querySelector('[data-testid="summary-balance"]')?.classList).not.toContain('text-danger');
    expect(el.textContent).toContain('Al día');
  });

  it('warns that the figures cover only the loaded orders when the history is partial (AC-05, EDGE-04)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(of({ total: 250, orders: [makeOrder()] }));
    const { el } = await open();
    expect(el.querySelector('[data-testid="summary-partial"]')?.textContent).toContain('Calculado con los 1 pedidos más recientes.');
  });

  it('shows no figures, not zeros, while loading or when the history failed (AC-03, EDGE-01)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(throwError(() => new Error('No se pudo cargar el historial de compras.')));
    const { el } = await open();
    expect(el.querySelector('[data-testid="purchase-summary"]')).toBeNull();
    expect(el.querySelector('[data-testid="summary-total"]')).toBeNull();
    expect(el.querySelector('[data-testid="new-order"]')).not.toBeNull();
  });

  it('does not offer a new order for an inactive customer (AC-07)', async () => {
    api.get.and.returnValue(of(makeCustomer({ active: false })));
    const { el } = await open();
    expect(el.querySelector('[data-testid="new-order"]')).toBeNull();
    expect(el.querySelector('[data-testid="history-create-first"]')).toBeNull();
  });

  it('hides the order actions and links when the Orders module is disabled (AC-07)', async () => {
    modulesState.salesDisabled = true;
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(of({ total: 1, orders: [makeOrder()] }));
    const { el } = await open();
    expect(el.querySelector('[data-testid="new-order"]')).toBeNull();
    expect(el.querySelector('[data-testid="history-all-orders"]')).toBeNull();
  });

  it('shows the purchase history section empty when the customer has no orders (AC-26)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { el } = await open();
    expect(ordersApi.list).toHaveBeenCalledOnceWith('c-1');
    expect(el.textContent).toContain('Historial de compras');
    expect(el.textContent).toContain('Este cliente aún no tiene pedidos.');
  });

  it('lists the real orders of the customer with a link to each one (AC-26)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(
      of({
        total: 2,
        orders: [
          makeOrder({ id: 'o2' }),
          makeOrder({ id: 'o1', date: '2026-09-01', total: '35.00', status: 'CANCELLED', paymentStatus: 'PENDING' }),
        ],
      }),
    );
    const { el } = await open();
    const rows = Array.from(el.querySelectorAll('app-customer-purchase-history tbody tr'));
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('A-0042');
    expect(rows[0].textContent).toContain('Bs 120.50');
    expect(rows[0].textContent).toContain('Entregado');
    expect(rows[0].textContent).toContain('Parcial');
    expect(rows[0].querySelector('a')?.getAttribute('href')).toBe('/pocketbiz/sales/orders/o2');
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });

  it('keeps the customer visible and explains when the history cannot be loaded (AC-26)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    ordersApi.list.and.returnValue(throwError(() => new Error('No se pudo cargar el historial de compras.')));
    const { el } = await open();
    expect(el.textContent).toContain('Ana Pérez');
    expect(el.querySelector('[data-testid="history-error"]')?.textContent).toContain('No se pudo cargar el historial');
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });

  it('asks Sales for the orders only after the customer is known, over HTTP (AC-26, ADR historial-compras)', async () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), 
        provideRouter([{ path: 'pocketbiz/customers/:id', component: CustomerDetailComponent }]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ToastrService, useValue: toastr },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/pocketbiz/customers/c-1', CustomerDetailComponent);
    const first = http.match(() => true);
    expect(first.map((r) => r.request.url)).toEqual(['/api/customers/c-1/']);
    first[0].flush({
      id: 'c-1', name: 'Ana', phone: '', email: '', notes: '', active: false,
      created_at: '2026-10-08T10:00:00Z', updated_at: '2026-10-08T10:00:00Z',
    });
    const orders = http.expectOne((r) => r.url === '/api/orders/');
    expect(orders.request.params.get('customer_id')).toBe('c-1');
    orders.flush({ count: 0, next: null, previous: null, results: [] });
    harness.detectChanges();
    http.verify();
  });

  it('shows an inactive customer and its history the same way (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer({ active: false })));
    const { el } = await open();
    expect(el.textContent).toContain('Inactivo');
    expect(el.querySelector('button.btn-warning')?.textContent?.trim()).toBe('Activar');
    expect(el.textContent).toContain('Historial de compras');
    expect(ordersApi.list).toHaveBeenCalledOnceWith('c-1');
  });

  it('warns and goes back to the list when the customer does not exist (AC-13)', async () => {
    api.get.and.returnValue(throwError(() => new CustomerApiError('Cliente no encontrado.', 404)));
    await open('nope');
    expect(toastr.error).toHaveBeenCalledWith('Cliente no encontrado.');
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/customers']);
  });

  it('deactivates after confirmation and refreshes the state (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    api.deactivate.and.returnValue(of(makeCustomer({ active: false })));
    const { component, harness } = await open();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();
    harness.detectChanges();

    expect(api.deactivate).toHaveBeenCalledOnceWith('c-1');
    expect(component.customer?.active).toBeFalse();
    expect(toastr.success).toHaveBeenCalledWith('Cliente desactivado');
  });

  it('does nothing when the confirmation is cancelled (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { component } = await open();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive();

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(api.activate).not.toHaveBeenCalled();
  });

  it('activates an inactive customer (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer({ active: false })));
    api.activate.and.returnValue(of(makeCustomer()));
    const { component } = await open();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive();

    expect(api.activate).toHaveBeenCalledOnceWith('c-1');
    expect(toastr.success).toHaveBeenCalledWith('Cliente activado');
  });
  it('shows the customer name of the confirmation dialog as plain text (EDGE-15, REV-01)', async () => {
    api.get.and.returnValue(of(makeCustomer({ name: '<img src=x onerror="window.__xss=1">' })));
    const { component } = await open();
    const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as SweetAlertResult);
    await (component as unknown as ToggleHook).confirmToggle(makeCustomer({ name: '<img src=x onerror="window.__xss=1">' }));
    const options = fire.calls.mostRecent().args[0] as unknown as Record<string, unknown>;
    expect(options['titleText']).toBe('¿Quieres desactivar a "<img src=x onerror="window.__xss=1">"?');
    expect(options['title']).toBeUndefined();
    expect(options['html']).toBeUndefined();
  });
});
