import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { of, throwError } from 'rxjs';

import { Product, ProductsApiService } from '../../../products';
import { Page } from '../../../../shared/models/page';
import { FieldErrors, Order } from '../../models/order';
import { makeItem, makeOrder } from '../../testing/order-fixtures';
import { LAST_ITEM_TOOLTIP, OrderItemsComponent } from './order-items.component';

const PRODUCT: Product = {
  id: 'p-9',
  name: 'Chipa',
  description: '',
  salePrice: '12.50',
  active: true,
  createdAt: '',
  updatedAt: '',
};

function page(results: Product[]): Page<Product> {
  return { count: results.length, next: null, previous: null, results };
}

describe('OrderItemsComponent', () => {
  let fixture: ComponentFixture<OrderItemsComponent>;
  let component: OrderItemsComponent;
  let api: jasmine.SpyObj<ProductsApiService>;

  function render(order: Order, busy = false, errors: FieldErrors = {}): HTMLElement {
    fixture = TestBed.createComponent(OrderItemsComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('order', order);
    fixture.componentRef.setInput('busy', busy);
    fixture.componentRef.setInput('errors', errors);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    api = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    api.list.and.returnValue(of(page([PRODUCT])));
    TestBed.configureTestingModule({
      imports: [OrderItemsComponent],
      providers: [{ provide: ProductsApiService, useValue: api }],
    });
  });

  it('lists the items with the snapshot name, unit price, quantity and server subtotal (AC-25)', () => {
    const element = render(makeOrder());
    const row = element.querySelector('[data-testid="item-row"]') as HTMLElement;
    const text = row.textContent?.replace(/\s+/g, ' ') ?? '';
    expect(text).toContain('Pack cuñapé');
    expect(text).toContain('Bs 35.00');
    expect(text).toContain('Bs 70.00');
    expect((row.querySelector('input') as HTMLInputElement).value).toBe('2');
  });

  it('only offers active products, starting with an initial list (AC-03, AC-25)', () => {
    render(makeOrder());
    expect(api.list).toHaveBeenCalledWith({ search: '', active: true, pageSize: 20 });
  });

  it('keeps working when the product search fails', () => {
    api.list.and.returnValue(throwError(() => new Error('boom')));
    expect(() => render(makeOrder())).not.toThrow();
  });

  it('shows the empty state asking for at least one product (AC-25)', () => {
    const element = render(makeOrder({ items: [] }));
    expect(element.querySelector('[data-testid="items-empty"]')?.textContent).toContain('al menos un producto');
    expect(element.querySelector('table')).toBeNull();
  });

  it('adds the chosen product with its quantity and resets the row (AC-03, AC-25)', () => {
    render(makeOrder());
    const added: { productId: string; quantity: number }[] = [];
    component.itemAdd.subscribe((event) => added.push(event));
    component.addForm.setValue({ product: PRODUCT, quantity: 3 });
    fixture.detectChanges();
    (fixture.debugElement.query(By.css('button.btn-primary')).nativeElement as HTMLButtonElement).click();
    expect(added).toEqual([{ productId: 'p-9', quantity: 3 }]);
    expect(component.addForm.getRawValue()).toEqual({ product: null, quantity: 1 });
  });

  it('does not add without a product, with an invalid quantity or while busy (AC-03)', () => {
    render(makeOrder());
    const added: unknown[] = [];
    component.itemAdd.subscribe((event) => added.push(event));
    component.add();
    component.addForm.setValue({ product: PRODUCT, quantity: 0 });
    component.add();
    fixture.componentRef.setInput('busy', true);
    component.addForm.setValue({ product: PRODUCT, quantity: 1 });
    component.add();
    expect(added).toEqual([]);
    const button = fixture.debugElement.query(By.css('button.btn-primary')).nativeElement as HTMLButtonElement;
    fixture.detectChanges();
    expect(button.disabled).toBeTrue();
  });

  it('emits a quantity change when the typed integer differs from the current one (AC-04)', () => {
    render(makeOrder());
    const changes: { quantity: number; id: string }[] = [];
    component.quantityChange.subscribe((e) => changes.push({ quantity: e.quantity, id: e.item.id }));
    const input = fixture.debugElement.query(By.css('[data-testid="item-row"] input')).nativeElement as HTMLInputElement;
    input.value = '5';
    input.dispatchEvent(new Event('change'));
    input.value = '2';
    input.dispatchEvent(new Event('change'));
    expect(changes).toEqual([{ quantity: 5, id: 'i-1' }]);
  });

  it('restores the field instead of emitting an invalid quantity (AC-04)', () => {
    render(makeOrder());
    const changes: unknown[] = [];
    component.quantityChange.subscribe((e) => changes.push(e));
    const input = fixture.debugElement.query(By.css('[data-testid="item-row"] input')).nativeElement as HTMLInputElement;
    for (const bad of ['0', '-3', '1.5', '']) {
      input.value = bad;
      input.dispatchEvent(new Event('change'));
      expect(input.value).toBe('2');
    }
    expect(changes).toEqual([]);
  });

  it('asks to remove an item (AC-05)', () => {
    render(makeOrder({ items: [makeItem(), makeItem({ id: 'i-2', productName: 'Chipa' })] }));
    const removed: string[] = [];
    component.itemRemove.subscribe((item) => removed.push(item.id));
    const buttons = fixture.debugElement.queryAll(By.css('[data-testid="item-row"] button'));
    (buttons[1].nativeElement as HTMLButtonElement).click();
    expect(removed).toEqual(['i-2']);
  });

  it('disables removing the last item of a confirmed order, with an explanation (AC-02)', () => {
    const element = render(makeOrder({ status: 'IN_PREPARATION' }));
    const button = element.querySelector('[data-testid="item-row"] button') as HTMLButtonElement;
    expect(button.disabled).toBeTrue();
    expect(button.title).toBe(LAST_ITEM_TOOLTIP);
  });

  it('allows emptying a NEW order (AC-02)', () => {
    const element = render(makeOrder());
    expect((element.querySelector('[data-testid="item-row"] button') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('is read-only when the order is not editable: no add row, no inputs, no remove (AC-19, AC-25)', () => {
    const element = render(makeOrder({ editable: false, status: 'DELIVERED' }));
    expect(element.querySelector('ng-select')).toBeNull();
    expect(element.querySelector('input')).toBeNull();
    expect(element.querySelector('button')).toBeNull();
    expect(element.querySelector('[data-testid="item-row"]')?.textContent).toContain('2');
  });

  it('shows the server errors for product and quantity (AC-03)', () => {
    const element = render(makeOrder(), false, {
      productId: ['El producto está inactivo.'],
      quantity: ['Mayor a cero'],
    });
    expect(element.querySelector('[data-testid="product-error"]')?.textContent).toContain('inactivo');
    expect(element.querySelector('[data-testid="quantity-error"]')?.textContent).toContain('Mayor a cero');
  });

  it('disables the quantity fields while busy', () => {
    const element = render(makeOrder(), true);
    expect((element.querySelector('[data-testid="item-row"] input') as HTMLInputElement).disabled).toBeTrue();
  });
});
