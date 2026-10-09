import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PAYMENT_STATUSES, PAYMENT_STATUS_LABELS, PaymentStatus } from '../../models/order';
import { PaymentStatusBadgeComponent } from './payment-status-badge.component';

describe('PaymentStatusBadgeComponent', () => {
  let fixture: ComponentFixture<PaymentStatusBadgeComponent>;

  function render(status: PaymentStatus): HTMLElement {
    fixture = TestBed.createComponent(PaymentStatusBadgeComponent);
    fixture.componentRef.setInput('status', status);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => TestBed.configureTestingModule({ imports: [PaymentStatusBadgeComponent] }));

  it('shows the label with the coins icon for every status (UI-04)', () => {
    for (const status of PAYMENT_STATUSES) {
      const element = render(status);
      expect(element.textContent?.trim()).toBe(PAYMENT_STATUS_LABELS[status]);
      expect(element.querySelector('i.fa-coins')).not.toBeNull();
    }
  });

  it('uses the DDR colors (UI-04)', () => {
    const colors: Record<PaymentStatus, string> = {
      PENDING: 'col-orange',
      PARTIAL: 'col-cyan',
      PAID: 'col-green',
      REFUNDED: 'col-purple',
    };
    for (const status of PAYMENT_STATUSES) {
      const badge = render(status).querySelector('div') as HTMLElement;
      expect(badge.classList).toContain('badge-outline');
      expect(badge.classList).toContain(colors[status]);
    }
  });
});
