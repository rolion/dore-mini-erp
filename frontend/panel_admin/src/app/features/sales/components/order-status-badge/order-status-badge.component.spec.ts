import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ORDER_STATUSES, ORDER_STATUS_LABELS, OrderStatus } from '../../models/order';
import { OrderStatusBadgeComponent } from './order-status-badge.component';

describe('OrderStatusBadgeComponent', () => {
  let fixture: ComponentFixture<OrderStatusBadgeComponent>;

  function render(status: OrderStatus): HTMLElement {
    fixture = TestBed.createComponent(OrderStatusBadgeComponent);
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [OrderStatusBadgeComponent] }));

  it('shows the label with the truck icon for every status (UI-04)', () => {
    for (const status of ORDER_STATUSES) {
      const element = render(status);
      expect(element.textContent?.trim()).toBe(ORDER_STATUS_LABELS[status]);
      expect(element.querySelector('i.fa-truck')).not.toBeNull();
    }
  });

  it('uses the DDR colors (UI-04)', () => {
    const colors: Record<OrderStatus, string> = {
      NEW: 'col-blue',
      IN_PREPARATION: 'col-orange',
      READY: 'col-indigo',
      DELIVERED: 'col-green',
      CANCELLED: 'col-red',
    };
    for (const status of ORDER_STATUSES) {
      const badge = render(status).querySelector('div') as HTMLElement;
      expect(badge.classList).toContain('badge-outline');
      expect(badge.classList).toContain(colors[status]);
    }
  });
});
