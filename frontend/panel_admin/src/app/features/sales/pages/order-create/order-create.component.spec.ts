import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ModulesService } from '../../../../core/service/modules.service';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { CustomerQuickCreateService, CustomersApiService } from '../../../customers';
import { Warehouse, WarehousesApiService } from '../../../inventory';
import { Product, ProductsApiService } from '../../../products';
import { OrderApiError, OrderRuleError, StartOrderInput } from '../../models/order';
import { OrdersApiService } from '../../services/orders-api.service';
import { NO_SALES_DEFAULTS, SalesDefaults, SalesSettingsService } from '../../services/sales-settings.service';
import { makeOrder } from '../../testing/order-fixtures';
import { OrderCreateComponent } from './order-create.component';

function product(overrides: Partial<Product> = {}): Product {
  return {
    id: 'p-1',
    name: 'Bolsas',
    description: '',
    salePrice: '10.00',
    category: 'finished',
    canBuy: false,
    canSell: true,
    needsReview: false,
    active: true,
    tracksStock: true,
    baseUnit: null,
    createdAt: '',
    updatedAt: '',
    ...overrides,
  };
}

const BAGS = product();
const SERVICE = product({ id: 'p-2', name: 'Instalación', salePrice: '50.00', tracksStock: false });
const CENTRAL: Warehouse = { id: 'w-1', name: 'Central', description: '', active: true, isDefault: true };
const SECOND: Warehouse = { id: 'w-2', name: 'Secundario', description: '', active: true, isDefault: false };

function page<T>(results: T[]): Page<T> {
  return { count: results.length, next: null, previous: null, results };
}

describe('OrderCreateComponent', () => {
  let fixture: ComponentFixture<OrderCreateComponent>;
  let component: OrderCreateComponent;
  let element: HTMLElement;
  let ordersApi: jasmine.SpyObj<OrdersApiService>;
  let productsApi: jasmine.SpyObj<ProductsApiService>;
  let warehousesApi: jasmine.SpyObj<WarehousesApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let navigate: jasmine.Spy;
  let defaults: SalesDefaults;
  let enabled: ReadonlySet<string>;
  const route = { snapshot: { paramMap: convertToParamMap({}), queryParamMap: convertToParamMap({}) } };

  function setup(): void {
    fixture = TestBed.createComponent(OrderCreateComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    element = fixture.nativeElement as HTMLElement;
  }

  function query(testId: string): HTMLElement | null {
    return element.querySelector(`[data-testid="${testId}"]`);
  }

  function text(testId: string): string {
    return (query(testId)?.textContent ?? '').trim();
  }

  function add(item: Product, quantity: number): void {
    component.addForm.setValue({ product: item, quantity });
    component.addLine();
    fixture.detectChanges();
  }

  function fillHeader(): void {
    component.form.patchValue({ salesChannel: 'WHATSAPP', orderDate: '2026-10-01' });
    fixture.detectChanges();
  }

  beforeEach(() => {
    ordersApi = jasmine.createSpyObj<OrdersApiService>('OrdersApiService', ['start']);
    productsApi = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    productsApi.list.and.returnValue(of(page([BAGS, SERVICE])));
    warehousesApi = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehousesApi.list.and.returnValue(of(page([CENTRAL, SECOND])));
    const customersApi = jasmine.createSpyObj<CustomersApiService>('CustomersApiService', ['list']);
    customersApi.list.and.returnValue(of(page([])));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    defaults = { ...NO_SALES_DEFAULTS, salesChannel: 'WHATSAPP', maxDiscountPercent: '10.00' };
    enabled = new Set(['sales', 'customers', 'inventory']);
    route.snapshot.queryParamMap = convertToParamMap({});
    TestBed.configureTestingModule({
      imports: [OrderCreateComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: OrdersApiService, useValue: ordersApi },
        { provide: ProductsApiService, useValue: productsApi },
        { provide: WarehousesApiService, useValue: warehousesApi },
        { provide: CustomersApiService, useValue: customersApi },
        {
          provide: ModulesService,
          useValue: {
            isDisabled: (key: string) => !enabled.has(key),
            get enabledKeysValue() {
              return enabled;
            },
          },
        },
        { provide: ToastrService, useValue: toastr },
        { provide: CustomerQuickCreateService, useValue: jasmine.createSpyObj('CustomerQuickCreateService', ['open']) },
        { provide: ActivatedRoute, useValue: route },
        { provide: SalesSettingsService, useValue: { defaults: () => of(defaults) } },
      ],
    });
    navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  });

  describe('structure (AC-01)', () => {
    it('shows header, detail block, totals and the start button on one screen', () => {
      setup();
      for (const id of ['order-channel', 'order-date', 'order-expected', 'order-warehouse', 'order-discount']) {
        expect(element.querySelector(`#${id}`)).withContext(id).not.toBeNull();
      }
      expect(element.querySelectorAll('ng-select').length).toBe(2); // cliente y producto
      expect(element.querySelector('[data-testid="add-line"]')).not.toBeNull();
      expect(text('subtotal')).toContain('0.00');
      expect(text('start-preparation')).toBe('Iniciar preparación');
      expect(text('items-empty')).toContain('al menos un producto');
    });

    it('preloads today, the default channel and the single/default warehouse', () => {
      setup();
      expect(component.form.controls.salesChannel.value).toBe('WHATSAPP');
      expect(component.form.controls.warehouseId.value).toBe('w-1');
    });

    it('hides the customer picker without Customers and the warehouse without Inventory (AC-09)', () => {
      enabled = new Set(['sales']);
      setup();
      expect(element.querySelectorAll('ng-select').length).toBe(1); // solo el de producto
      expect(element.querySelector('#order-warehouse')).toBeNull();
      expect(warehousesApi.list).not.toHaveBeenCalled();
    });
  });

  describe('detail and totals (AC-02, AC-03)', () => {
    it('adds a product with its subtotal and sums the quantity of an already listed one', () => {
      setup();
      add(BAGS, 2);
      add(BAGS, 1);
      expect(component.lines.length).toBe(1);
      expect(component.lines[0].quantity).toBe(3);
      expect(element.querySelectorAll('[data-testid="line-row"]').length).toBe(1);
      expect(text('subtotal')).toContain('30.00');
      expect(component.addForm.getRawValue()).toEqual({ product: null, quantity: 1 });
    });

    it('edits the quantity, rejects invalid ones and removes a row', () => {
      setup();
      add(BAGS, 2);
      const input = element.querySelector<HTMLInputElement>('tbody input')!;
      input.value = '5';
      input.dispatchEvent(new Event('change'));
      fixture.detectChanges();
      expect(text('subtotal')).toContain('50.00');
      input.value = '0';
      input.dispatchEvent(new Event('change'));
      expect(component.lines[0].quantity).toBe(5);
      expect(input.value).toBe('5');
      element.querySelector<HTMLButtonElement>('tbody button')!.click();
      fixture.detectChanges();
      expect(component.lines).toEqual([]);
      expect(query('items-empty')).not.toBeNull();
    });

    it('shows total = subtotal − discount', () => {
      setup();
      add(BAGS, 2);
      component.discountControl.setValue('2.00');
      fixture.detectChanges();
      expect(text('total')).toContain('18.00');
    });
  });

  describe('discount limit (AC-04)', () => {
    it('shows the maximum allowed and blocks a discount above it', () => {
      setup();
      add(BAGS, 10); // 100.00 → máximo 10 %
      expect(text('discount-hint')).toContain('10');
      expect(text('discount-hint')).toContain('10.00');
      component.discountControl.setValue('10.01');
      fixture.detectChanges();
      expect(text('discount-error')).toContain('máximo');
      expect(component.canSubmit).toBeFalse();
      component.discountControl.setValue('10.00');
      fixture.detectChanges();
      expect(query('discount-error')).toBeNull();
    });
  });

  describe('start preparation (AC-05, AC-06)', () => {
    it('is disabled without products, without channel or without a required warehouse', () => {
      setup();
      fillHeader();
      expect(component.canSubmit).toBeFalse();
      add(BAGS, 1);
      expect(component.canSubmit).toBeTrue();
      component.form.controls.warehouseId.setValue('');
      expect(component.canSubmit).toBeFalse();
      component.form.controls.warehouseId.setValue('w-1');
      component.form.controls.salesChannel.setValue('');
      expect(component.canSubmit).toBeFalse();
    });

    it('does not require a warehouse when no product controls stock', () => {
      setup();
      fillHeader();
      component.form.controls.warehouseId.setValue('');
      add(SERVICE, 1);
      expect(component.warehouseRequired).toBeFalse();
      expect(component.canSubmit).toBeTrue();
    });

    it('creates the whole order in one call and goes to its detail', () => {
      ordersApi.start.and.returnValue(of(makeOrder({ id: 'o-9', status: 'IN_PREPARATION' })));
      setup();
      fillHeader();
      add(BAGS, 2);
      add(SERVICE, 1);
      component.discountControl.setValue('3.00');
      component.form.controls.warehouseId.setValue('w-2');
      component.form.controls.notes.setValue(' Entregar temprano ');
      component.onSubmit();
      const sent = ordersApi.start.calls.mostRecent().args[0] as StartOrderInput;
      expect(sent).toEqual({
        customerId: null,
        salesChannel: 'WHATSAPP',
        orderDate: '2026-10-01',
        expectedDeliveryDate: null,
        notes: 'Entregar temprano',
        warehouseId: 'w-2',
        discount: '3.00',
        items: [
          { productId: 'p-1', quantity: 2 },
          { productId: 'p-2', quantity: 1 },
        ],
      });
      expect(toastr.success).toHaveBeenCalled();
      expect(navigate).toHaveBeenCalledWith(['/pocketbiz/sales/orders', 'o-9']);
      expect(component.hasUnsavedChanges()).toBeFalse();
    });

    it('never submits twice while saving and sends no warehouse without Inventory (AC-09)', () => {
      enabled = new Set(['sales', 'customers']);
      ordersApi.start.and.returnValue(of(makeOrder()));
      setup();
      fillHeader();
      add(BAGS, 1);
      component.onSubmit();
      expect((ordersApi.start.calls.mostRecent().args[0] as StartOrderInput).warehouseId).toBeNull();
      component.saving = true;
      component.onSubmit();
      expect(ordersApi.start).toHaveBeenCalledTimes(1);
    });

    it('keeps what was typed and explains the missing stock on a 409 (AC-06)', () => {
      const shortage = { productId: 'p-1', productName: 'Bolsas', unit: 'u', requested: '4.0000', available: '1.0000' };
      ordersApi.start.and.returnValue(
        throwError(() => new OrderRuleError('Sin stock', 'insufficient_stock', [shortage], 'Central')),
      );
      setup();
      fillHeader();
      add(BAGS, 4);
      add(SERVICE, 1);
      component.onSubmit();
      fixture.detectChanges();
      expect(navigate).not.toHaveBeenCalled();
      expect(component.lines.length).toBe(2);
      expect(text('stock-alert')).toContain('Central');
      expect(text('stock-alert')).toContain('Bolsas');
      const rows = element.querySelectorAll('[data-testid="line-row"]');
      expect(rows[0].classList).toContain('table-warning');
      expect(rows[1].classList).not.toContain('table-warning');
      expect(component.saving).toBeFalse();
    });

    it('keeps what was typed and explains a fiscal period block on a 409 (AC-13, UI-03)', () => {
      ordersApi.start.and.returnValue(throwError(() => new OrderRuleError('x', 'fiscal_period_closed')));
      setup();
      fillHeader();
      add(BAGS, 1);
      component.onSubmit();
      fixture.detectChanges();
      expect(navigate).not.toHaveBeenCalled();
      expect(component.lines.length).toBe(1);
      expect(text('fiscal-period-message')).toContain('está cerrado');
      expect(component.saving).toBeFalse();
      fillHeader();
      component.form.controls.notes.setValue('cambió algo');
      fixture.detectChanges();
      expect(element.querySelector('[data-testid="alert-fiscal-period"]')).toBeNull();
    });

    it('marks only the short product when two products share a name (REV-09)', () => {
      const twin = product({ id: 'p-3', name: 'Bolsas', tracksStock: true });
      const shortage = { productId: 'p-3', productName: 'Bolsas', unit: 'u', requested: '4.0000', available: '1.0000' };
      ordersApi.start.and.returnValue(throwError(() => new OrderRuleError('Sin stock', 'insufficient_stock', [shortage], 'Central')));
      setup();
      fillHeader();
      add(BAGS, 1);
      add(twin, 4);
      component.onSubmit();
      fixture.detectChanges();
      const rows = element.querySelectorAll('[data-testid="line-row"]');
      expect(rows[0].classList).not.toContain('table-warning');
      expect(rows[1].classList).toContain('table-warning');
    });

    it('shows server field errors without clearing the form and a toast for other failures', () => {
      ordersApi.start.and.returnValue(
        throwError(
          () => new OrderApiError('Revisa', 400, { discount: ['Tope superado.'], warehouseId: ['Almacén inválido.'], items: ['Línea 1: x'] }),
        ),
      );
      setup();
      fillHeader();
      add(BAGS, 1);
      component.onSubmit();
      fixture.detectChanges();
      expect(text('discount-error')).toContain('Tope superado.');
      expect(text('warehouse-error')).toContain('Almacén inválido.');
      expect(text('items-error')).toContain('Línea 1: x');
      expect(component.lines.length).toBe(1);

      ordersApi.start.and.returnValue(throwError(() => new OrderApiError('Sin conexión', 0)));
      component.onSubmit();
      expect(toastr.error).toHaveBeenCalledWith('Sin conexión');
    });
  });

  describe('leaving the screen (UI-05)', () => {
    it('asks for confirmation only when there is something typed', () => {
      setup();
      expect(component.hasUnsavedChanges()).toBeFalse();
      add(BAGS, 1);
      expect(component.hasUnsavedChanges()).toBeTrue();
    });
  });
});
