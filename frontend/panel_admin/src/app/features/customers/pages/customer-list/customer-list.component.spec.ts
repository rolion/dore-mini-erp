import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import Swal, { SweetAlertResult } from 'sweetalert2';
import { of, throwError } from 'rxjs';

import { Customer, CustomerApiError } from '../../models/customer';
import { Page } from '../../../../shared/models/page';
import { CustomersApiService } from '../../services/customers-api.service';
import { makeCustomer } from '../../testing/customer-fixtures';
import { CustomerListComponent } from './customer-list.component';

interface ToggleHook {
  confirmToggle(customer: Customer): Promise<boolean>;
}

function page(results: Customer[], count = results.length): Page<Customer> {
  return { count, next: null, previous: null, results };
}

describe('CustomerListComponent', () => {
  let fixture: ComponentFixture<CustomerListComponent>;
  let component: CustomerListComponent;
  let api: jasmine.SpyObj<CustomersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  const active = makeCustomer({ id: 'a', name: 'Ana Pérez' });
  const inactive = makeCustomer({ id: 'b', name: 'Beto', phone: '', email: '', active: false });

  beforeEach(async () => {
    api = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['list', 'activate', 'deactivate']);
    api.list.and.returnValue(of(page([active, inactive])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [CustomerListComponent],
      providers: [
        provideRouter([]),
        { provide: CustomersApiService, useValue: api },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(CustomerListComponent);
    component = fixture.componentInstance;
  });

  function lastListParams() {
    return api.list.calls.mostRecent().args[0];
  }

  it('loads only active customers by default, 10 per page (AC-10, REQ-CUS-005)', () => {
    fixture.detectChanges();

    expect(api.list).toHaveBeenCalledOnceWith({ search: '', active: true, page: 1, pageSize: 10 });
    expect(component.statusControl.value).toBe('active');
  });

  it('shows name, phone, email and state, with dashes for empty contact (AC-10)', () => {
    fixture.detectChanges();
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Ana Pérez');
    expect(text).toContain('+59176543210');
    expect(text).toContain('ana@example.com');
    expect(text).toContain('Activo');
    expect(text).toContain('Inactivo');
    expect(text).toContain('—');
    expect(component.total).toBe(2);
  });

  it('offers Activos, Inactivos and Todos in the state filter, Activos first (AC-10)', () => {
    fixture.detectChanges();
    const options = fixture.debugElement
      .queryAll(By.css('select option'))
      .map((o) => (o.nativeElement as HTMLOptionElement).textContent?.trim());
    expect(options).toEqual(['Activos', 'Inactivos', 'Todos']);
  });

  it('links the "+" button to the new customer form (AC-10)', () => {
    fixture.detectChanges();
    const link = fixture.debugElement.query(By.css('a[title="Nuevo cliente"]'));
    expect((link.nativeElement as HTMLAnchorElement).getAttribute('href')).toBe('/customers/new');
  });

  it('searches by name or phone with a single debounced field and goes back to page 1 (AC-10, REQ-CUS-003)', fakeAsync(() => {
    fixture.detectChanges();
    component.onPage({ offset: 2 });
    expect(lastListParams()?.page).toBe(3);

    component.searchControl.setValue('  765 ');
    tick(299);
    expect(api.list).toHaveBeenCalledTimes(2);
    tick(1);

    expect(api.list).toHaveBeenCalledTimes(3);
    expect(lastListParams()).toEqual({ search: '765', active: true, page: 1, pageSize: 10 });
  }));

  it('maps the state filter to the active parameter (AC-10)', () => {
    fixture.detectChanges();

    component.statusControl.setValue('inactive');
    expect(lastListParams()?.active).toBeFalse();

    component.statusControl.setValue('all');
    expect(lastListParams()?.active).toBeUndefined();

    component.statusControl.setValue('active');
    expect(lastListParams()?.active).toBeTrue();
  });

  it('requests the selected page (server-side pagination) and ignores repeated events (AC-10)', () => {
    fixture.detectChanges();
    component.onPage({ offset: 0 });
    expect(api.list).toHaveBeenCalledTimes(1);

    component.onPage({ offset: 1 });
    expect(lastListParams()?.page).toBe(2);
  });

  it('shows the empty state message (AC-10)', () => {
    api.list.and.returnValue(of(page([])));
    fixture.detectChanges();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('No hay clientes que coincidan');
  });

  it('shows a toast when loading fails (AC-10)', () => {
    api.list.and.returnValue(throwError(() => new CustomerApiError('Sin conexión', 0)));
    fixture.detectChanges();
    expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    expect(component.loading).toBeFalse();
  });

  it('deactivates after confirmation, notifies and reloads (AC-10)', async () => {
    api.deactivate.and.returnValue(of({ ...active, active: false }));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(active);

    expect(api.deactivate).toHaveBeenCalledOnceWith('a');
    expect(toastr.success).toHaveBeenCalledWith('Cliente desactivado');
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('activates an inactive customer after confirmation (AC-10)', async () => {
    api.activate.and.returnValue(of({ ...inactive, active: true }));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(inactive);

    expect(api.activate).toHaveBeenCalledOnceWith('b');
    expect(toastr.success).toHaveBeenCalledWith('Cliente activado');
  });

  it('does nothing when the confirmation is cancelled (AC-10)', async () => {
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(false);

    await component.toggleActive(active);

    expect(api.deactivate).not.toHaveBeenCalled();
    expect(api.list).toHaveBeenCalledTimes(1);
  });

  it('shows a toast when toggling fails (AC-10)', async () => {
    api.deactivate.and.returnValue(throwError(() => new CustomerApiError('Cliente no encontrado.', 404)));
    fixture.detectChanges();
    spyOn(component as unknown as ToggleHook, 'confirmToggle').and.resolveTo(true);

    await component.toggleActive(active);

    expect(toastr.error).toHaveBeenCalledWith('Cliente no encontrado.');
  });
  it('shows the customer name of the confirmation dialog as plain text (EDGE-15, REV-01)', async () => {
    fixture.detectChanges();
    const fire = spyOn(Swal, 'fire').and.resolveTo({ isConfirmed: true } as SweetAlertResult);
    const customer = makeCustomer({ name: '<img src=x onerror="window.__xss=1">' });
    await (component as unknown as ToggleHook).confirmToggle(customer);
    const options = fire.calls.mostRecent().args[0] as unknown as Record<string, unknown>;
    expect(options['titleText']).toBe('¿Quieres desactivar a "<img src=x onerror="window.__xss=1">"?');
    expect(options['title']).toBeUndefined();
    expect(options['html']).toBeUndefined();
  });
});
