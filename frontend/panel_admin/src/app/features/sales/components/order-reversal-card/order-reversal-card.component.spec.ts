import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { makeOrder } from '../../testing/order-fixtures';
import { OrderReversalCardComponent } from './order-reversal-card.component';

describe('OrderReversalCardComponent', () => {
  let fixture: ComponentFixture<OrderReversalCardComponent>;

  function render(order = makeOrder()): HTMLElement {
    fixture = TestBed.createComponent(OrderReversalCardComponent);
    fixture.componentRef.setInput('order', order);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  function q(element: HTMLElement, id: string): HTMLElement | null {
    return element.querySelector(`[data-testid="${id}"]`);
  }

  beforeEach(() => TestBed.configureTestingModule({
    imports: [OrderReversalCardComponent],
    providers: [...provideTestTranslations(), provideRouter([])],
  }));

  it('shows when, who and why for a return, the external refund and the linked records (AC-09)', () => {
    const element = render(makeOrder({
      status: 'RETURNED', returnedAt: '2026-10-04T10:00:00Z', returnedByName: 'ana', returnReason: 'Defectuoso',
      refundAcknowledged: true,
      reversal: {
        movements: [{ id: 'm-1', productName: 'Bolsas', quantity: '2.0000', unit: 'u', warehouseName: 'Central',
          reversedById: 'm-2', reversedByReference: 'REV-1' }],
        entries: [
          { event: 'SALE_DELIVERY', id: 'e-1', accountingDate: '2026-10-03', description: 'x', total: '70.00', reversedById: 'e-3' },
          { event: 'SALE_PAYMENT', id: 'e-2', accountingDate: '2026-10-03', description: 'y', total: '20.00', reversedById: null },
        ],
      },
    }));
    expect(q(element, 'reversal-user')?.textContent).toContain('ana');
    expect(q(element, 'reversal-reason')?.textContent).toContain('Defectuoso');
    expect(q(element, 'reversal-refund')).not.toBeNull();
    expect(element.querySelector('[data-testid="reversal-movement"] a[href$="/inventory/movements/m-2"]')).not.toBeNull();
    const entries = element.querySelectorAll('[data-testid="reversal-entry"]');
    expect(entries.length).toBe(2);
    expect(entries[0].querySelector('a[href$="/accounting/journal/e-3"]')).not.toBeNull();
    expect(entries[1].textContent).toContain('Sin reverso');
  });

  it('shows a cancellation with its own date, user and reason and no refund line without payments', () => {
    const element = render(makeOrder({
      status: 'CANCELLED', cancelledAt: '2026-10-04T10:00:00Z', cancelledByName: 'beto', cancellationReason: 'Ya no lo quiere',
    }));
    expect(q(element, 'reversal-user')?.textContent).toContain('beto');
    expect(q(element, 'reversal-reason')?.textContent).toContain('Ya no lo quiere');
    expect(q(element, 'reversal-refund')).toBeNull();
    expect(q(element, 'reversal-movement')).toBeNull();
  });
});
