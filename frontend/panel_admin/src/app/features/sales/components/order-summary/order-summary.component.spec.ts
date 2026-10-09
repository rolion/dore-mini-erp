import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';

import { Order } from '../../models/order';
import { makeOrder } from '../../testing/order-fixtures';
import { OrderSummaryComponent } from './order-summary.component';

describe('OrderSummaryComponent', () => {
  let fixture: ComponentFixture<OrderSummaryComponent>;

  function render(order: Order, busy = false, errors = {}): HTMLElement {
    fixture = TestBed.createComponent(OrderSummaryComponent);
    fixture.componentRef.setInput('order', order);
    fixture.componentRef.setInput('busy', busy);
    fixture.componentRef.setInput('errors', errors);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function text(element: HTMLElement, id: string): string {
    return element.querySelector(`[data-testid="${id}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [OrderSummaryComponent] }));

  it('shows the amounts exactly as the server calculated them (AC-25, UI-05)', () => {
    const element = render(
      makeOrder({ subtotal: '70.00', discount: '10.00', total: '60.00', paidTotal: '25.00', balance: '35.00' }),
    );
    expect(text(element, 'subtotal')).toBe('Bs 70.00');
    expect(text(element, 'total')).toBe('Bs 60.00');
    expect(text(element, 'paid')).toBe('Bs 25.00');
    expect(text(element, 'balance')).toBe('Bs 35.00');
    expect((fixture.componentInstance.discountControl.value)).toBe('10.00');
  });

  it('never offers the total as an editable field (AC-06)', () => {
    const element = render(makeOrder());
    const inputs = element.querySelectorAll('input');
    expect(inputs.length).toBe(1);
    expect(element.querySelector('[data-testid="total"] input')).toBeNull();
  });

  it('emits the typed discount when applying while editable (AC-25)', () => {
    render(makeOrder());
    const emitted: string[] = [];
    fixture.componentInstance.discountSubmit.subscribe((value) => emitted.push(value));
    fixture.componentInstance.discountControl.setValue(' 5.50 ');
    (fixture.debugElement.query(By.css('button')).nativeElement as HTMLButtonElement).click();
    expect(emitted).toEqual(['5.50']);
  });

  it('does not emit while busy or when the field is empty (AC-25)', () => {
    render(makeOrder(), true);
    const emitted: string[] = [];
    fixture.componentInstance.discountSubmit.subscribe((value) => emitted.push(value));
    fixture.componentInstance.discountControl.setValue('5.00');
    fixture.componentInstance.submitDiscount();
    fixture.componentInstance.discountControl.setValue('  ');
    fixture.componentRef.setInput('busy', false);
    fixture.componentInstance.submitDiscount();
    expect(emitted).toEqual([]);
  });

  it('shows the discount as read-only text when the order is not editable (AC-19)', () => {
    const element = render(makeOrder({ editable: false, discount: '10.00' }));
    expect(element.querySelector('input')).toBeNull();
    expect(element.querySelector('button')).toBeNull();
    expect(text(element, 'discount')).toBe('Bs 10.00');
  });

  it('shows the server error under the discount field (AC-07)', () => {
    const element = render(makeOrder(), false, { discount: ['El descuento no puede superar el subtotal.'] });
    expect(text(element, 'discount-error')).toBe('El descuento no puede superar el subtotal.');
  });
});
