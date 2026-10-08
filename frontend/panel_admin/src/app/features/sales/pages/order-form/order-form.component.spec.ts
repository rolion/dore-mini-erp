import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { Customer, CustomersApiService } from '../../../customers';
import { Order, OrderApiError, todayIso } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { makeOrder } from '../../testing/order-fixtures';
import { CUSTOMER_SEARCH_PAGE_SIZE } from '../../services/customer-options.service';
import { NOT_EDITABLE_MESSAGE, OrderFormComponent } from './order-form.component';

const CUSTOMER: Customer = {
  id: 'c-2',
  name: 'Luis Gómez',
  phone: '+59170000000',
  email: '',
  notes: '',
  active: true,
  createdAt: '',
  updatedAt: '',
};

function page(results: Customer[]): Page<Customer> {
  return { count: results.length, next: null, previous: null, results };
}

describe('OrderFormComponent', () => {
  let fixture: ComponentFixture<OrderFormComponent>;
  let component: OrderFormComponent;
  let ordersApi: jasmine.SpyObj<OrdersApiService>;
  let customersApi: jasmine.SpyObj<CustomersApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;
  const route = { snapshot: { paramMap: convertToParamMap({}) } };

  function setup(id: string | null = null): HTMLElement {
    route.snapshot.paramMap = convertToParamMap(id ? { id } : {});
    fixture = TestBed.createComponent(OrderFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function fillValid(): void {
    component.form.patchValue({ salesChannel: 'WHATSAPP', orderDate: '2026-10-01' });
  }

  beforeEach(() => {
    ordersApi = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['get', 'create', 'update']);
    customersApi = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['list']);
    customersApi.list.and.returnValue(of(page([CUSTOMER])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [OrderFormComponent],
      providers: [
        provideRouter([]),
        { provide: OrdersApiService, useValue: ordersApi },
        { provide: CustomersApiService, useValue: customersApi },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: route },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  describe('create', () => {
    it('starts with today as the order date, no customer and no channel (AC-24)', () => {
      setup();
      expect(component.isEdit).toBeFalse();
      expect(component.form.getRawValue()).toEqual({
        customer: null,
        salesChannel: '',
        orderDate: todayIso(),
        expectedDeliveryDate: '',
        notes: '',
      });
    });

    it('offers the six channels with their Spanish labels (AC-08, AC-24)', () => {
      const element = setup();
      const options = Array.from(element.querySelectorAll('#order-channel option')).map((o) => o.textContent?.trim());
      expect(options).toEqual(['Seleccione un canal', 'WhatsApp', 'Facebook', 'Instagram', 'Venta directa', 'Feria', 'Otro']);
    });

    it('searches only active customers, starting with an initial list (AC-24)', () => {
      setup();
      expect(customersApi.list).toHaveBeenCalledWith({ search: '', active: true, pageSize: CUSTOMER_SEARCH_PAGE_SIZE });
    });

    it('survives a failing customer search', () => {
      customersApi.list.and.returnValue(throwError(() => new Error('boom')));
      expect(() => setup()).not.toThrow();
    });

    it('requires a channel and a date before saving (AC-24)', () => {
      const element = setup();
      const button = element.querySelector('button[type="submit"]') as HTMLButtonElement;
      expect(button.disabled).toBeTrue();
      component.form.patchValue({ salesChannel: 'STORE', orderDate: '' });
      fixture.detectChanges();
      expect(button.disabled).toBeTrue();
      component.form.patchValue({ orderDate: '2026-10-01' });
      fixture.detectChanges();
      expect(button.disabled).toBeFalse();
    });

    it('creates the order without customer or delivery date and opens its detail (AC-01, AC-24)', () => {
      ordersApi.create.and.returnValue(of(makeOrder({ id: 'o-9' })));
      setup();
      fillValid();
      component.form.patchValue({ notes: '  Sin picante ' });
      component.onSubmit();
      expect(ordersApi.create).toHaveBeenCalledOnceWith({
        customerId: null,
        salesChannel: 'WHATSAPP',
        orderDate: '2026-10-01',
        expectedDeliveryDate: null,
        notes: 'Sin picante',
      });
      expect(toastr.success).toHaveBeenCalledWith('Pedido creado');
      expect(navigate).toHaveBeenCalledWith(['/sales/orders', 'o-9']);
    });

    it('sends the chosen customer and the expected delivery date (AC-01, AC-18)', () => {
      ordersApi.create.and.returnValue(of(makeOrder()));
      setup();
      fillValid();
      component.form.patchValue({ customer: { id: 'c-2', name: 'Luis Gómez' }, expectedDeliveryDate: '2026-10-05' });
      component.onSubmit();
      expect(ordersApi.create.calls.mostRecent().args[0]).toEqual(
        jasmine.objectContaining({ customerId: 'c-2', expectedDeliveryDate: '2026-10-05' }),
      );
    });

    it('selects a customer created from the order (AC-27)', () => {
      setup();
      component.selectCustomer({ id: 'c-7', name: 'Nuevo' });
      expect(component.form.controls.customer.value).toEqual({ id: 'c-7', name: 'Nuevo' });
    });

    it('does not submit an invalid form nor twice while saving (AC-24)', () => {
      const pending = new Subject<Order>();
      ordersApi.create.and.returnValue(pending);
      setup();
      component.onSubmit();
      expect(ordersApi.create).not.toHaveBeenCalled();
      fillValid();
      component.onSubmit();
      component.onSubmit();
      expect(ordersApi.create).toHaveBeenCalledTimes(1);
      expect(component.saving).toBeTrue();
    });

    it('shows the server errors under each field, together, and clears them when editing (AC-24)', () => {
      ordersApi.create.and.returnValue(
        throwError(
          () =>
            new OrderApiError('Revisa los datos', 400, {
              customerId: ['El cliente está inactivo.'],
              expectedDeliveryDate: ['No puede ser anterior al pedido.'],
              salesChannel: ['Canal inválido.'],
              orderDate: ['Fecha inválida.'],
              notes: ['Muy larga.'],
            }),
        ),
      );
      const element = setup();
      fillValid();
      component.onSubmit();
      fixture.detectChanges();
      const text = (id: string) => element.querySelector(`[data-testid="${id}"]`)?.textContent?.trim();
      expect(text('customer-error')).toBe('El cliente está inactivo.');
      expect(text('expected-error')).toBe('No puede ser anterior al pedido.');
      expect(text('channel-error')).toBe('Canal inválido.');
      expect(text('order-date-error')).toBe('Fecha inválida.');
      expect(text('notes-error')).toBe('Muy larga.');
      expect(toastr.error).not.toHaveBeenCalled();
      expect(component.saving).toBeFalse();
      component.form.patchValue({ notes: 'cambio' });
      expect(component.serverErrors).toEqual({});
    });

    it('toasts errors that are not tied to a field', () => {
      ordersApi.create.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
      setup();
      fillValid();
      component.onSubmit();
      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    });
  });

  describe('edit', () => {
    it('loads the order and fills the form, keeping the current customer (AC-24)', () => {
      ordersApi.get.and.returnValue(of(makeOrder({ expectedDeliveryDate: null, notes: 'Nota' })));
      setup('o-1');
      expect(ordersApi.get).toHaveBeenCalledOnceWith('o-1');
      expect(component.isEdit).toBeTrue();
      expect(component.form.getRawValue()).toEqual({
        customer: { id: 'c-1', name: 'Ana Pérez' },
        salesChannel: 'WHATSAPP',
        orderDate: '2026-10-01',
        expectedDeliveryDate: '',
        notes: 'Nota',
      });
    });

    it('updates and goes back to the detail (AC-10, AC-24)', () => {
      ordersApi.get.and.returnValue(of(makeOrder()));
      ordersApi.update.and.returnValue(of(makeOrder()));
      setup('o-1');
      component.form.patchValue({ customer: null, expectedDeliveryDate: '' });
      component.onSubmit();
      expect(ordersApi.update).toHaveBeenCalledOnceWith('o-1', {
        customerId: null,
        salesChannel: 'WHATSAPP',
        orderDate: '2026-10-01',
        expectedDeliveryDate: null,
        notes: 'Sin picante',
      });
      expect(toastr.success).toHaveBeenCalledWith('Pedido actualizado');
      expect(navigate).toHaveBeenCalledWith(['/sales/orders', 'o-1']);
    });

    it('goes back to the list when the order does not exist (EDGE-12)', () => {
      ordersApi.get.and.returnValue(throwError(() => new OrderApiError('Pedido no encontrado.', 404)));
      setup('nope');
      expect(toastr.error).toHaveBeenCalledWith('Pedido no encontrado.');
      expect(navigate).toHaveBeenCalledWith(['/sales/orders']);
    });

    it('sends the user to the detail when the order is no longer editable (AC-19, AC-24)', () => {
      ordersApi.get.and.returnValue(of(makeOrder({ editable: false, status: 'DELIVERED' })));
      setup('o-1');
      expect(toastr.error).toHaveBeenCalledWith(NOT_EDITABLE_MESSAGE);
      expect(navigate).toHaveBeenCalledWith(['/sales/orders', 'o-1']);
    });

    it('links Cancelar back to the order', () => {
      ordersApi.get.and.returnValue(of(makeOrder()));
      const element = setup('o-1');
      fixture.detectChanges();
      const cancel = Array.from(element.querySelectorAll('a')).find((a) => a.textContent?.trim() === 'Cancelar');
      expect(cancel?.getAttribute('href')).toBe('/sales/orders/o-1');
    });
  });
});
