import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { provideHttpClient } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { RouterTestingHarness } from '@angular/router/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Customer, CustomerApiError } from '../../models/customer';
import { CustomersApiService } from '../../services/customers-api.service';
import { makeCustomer } from '../../testing/customer-fixtures';
import { CustomerDetailComponent } from './customer-detail.component';

interface ToggleHook {
  confirmToggle(customer: Customer): Promise<boolean>;
}

describe('CustomerDetailComponent', () => {
  let api: jasmine.SpyObj<CustomersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;

  beforeEach(() => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['get', 'activate', 'deactivate']);
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'customers/:id', component: CustomerDetailComponent }]),
        { provide: CustomersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  async function open(id = 'c-1') {
    const harness = await RouterTestingHarness.create();
    const component = await harness.navigateByUrl(`/customers/${id}`, CustomerDetailComponent);
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
    const editLink = el.querySelector('a.btn-primary') as HTMLAnchorElement;
    expect(editLink.getAttribute('href')).toBe('/customers/c-1/edit');
    expect(el.querySelector('button.btn-warning')?.textContent?.trim()).toBe('Desactivar');
    expect(el.textContent).toContain('Volver');
  });

  it('shows dashes and "Sin notas" for empty optional fields (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer({ phone: '', email: '', notes: '' })));
    const { el } = await open();
    expect(el.textContent).toContain('Sin notas');
    expect((el.textContent ?? '').match(/—/g)?.length).toBe(2);
  });

  it('shows the purchase history section empty and never asks for orders (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer()));
    const { el } = await open();
    expect(el.textContent).toContain('Historial de compras');
    expect(el.textContent).toContain('Este cliente aún no tiene pedidos.');
  });

  it('does not issue any HTTP request for orders (AC-13, ADR historial-compras)', async () => {
    TestBed.resetTestingModule();
    TestBed.configureTestingModule({
      providers: [
        provideRouter([{ path: 'customers/:id', component: CustomerDetailComponent }]),
        provideHttpClient(),
        provideHttpClientTesting(),
        { provide: ToastrService, useValue: toastr },
      ],
    });
    const http = TestBed.inject(HttpTestingController);
    const harness = await RouterTestingHarness.create();
    await harness.navigateByUrl('/customers/c-1', CustomerDetailComponent);
    const requests = http.match(() => true);
    expect(requests.map((r) => r.request.url)).toEqual(['/api/customers/c-1/']);
    requests[0].flush({
      id: 'c-1', name: 'Ana', phone: '', email: '', notes: '', active: false,
      created_at: '2026-10-08T10:00:00Z', updated_at: '2026-10-08T10:00:00Z',
    });
    harness.detectChanges();
    http.expectNone((r) => r.url.includes('orders'));
    http.verify();
  });

  it('shows an inactive customer and its history the same way (AC-13)', async () => {
    api.get.and.returnValue(of(makeCustomer({ active: false })));
    const { el } = await open();
    expect(el.textContent).toContain('Inactivo');
    expect(el.querySelector('button.btn-warning')?.textContent?.trim()).toBe('Activar');
    expect(el.textContent).toContain('Historial de compras');
  });

  it('warns and goes back to the list when the customer does not exist (AC-13)', async () => {
    api.get.and.returnValue(throwError(() => new CustomerApiError('Cliente no encontrado.', 404)));
    await open('nope');
    expect(toastr.error).toHaveBeenCalledWith('Cliente no encontrado.');
    expect(navigate).toHaveBeenCalledWith(['/customers']);
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
});
