import { TestBed } from '@angular/core/testing';

import { CustomerOrderSummary } from '../../models/customer';
import { CustomerPurchaseHistoryComponent } from './customer-purchase-history.component';

describe('CustomerPurchaseHistoryComponent', () => {
  function render(orders?: CustomerOrderSummary[]): HTMLElement {
    const fixture = TestBed.createComponent(CustomerPurchaseHistoryComponent);
    if (orders) fixture.componentRef.setInput('orders', orders);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  it('shows the empty message when there are no orders (AC-13)', () => {
    const el = render();
    expect(el.textContent).toContain('Historial de compras');
    expect(el.textContent).toContain('Este cliente aún no tiene pedidos.');
    expect(el.querySelector('table')).toBeNull();
  });

  it('lists date, total and status of each order (AC-13)', () => {
    const el = render([
      { id: 'o1', date: '2026-10-05T12:00:00Z', total: '120.50', status: 'Entregado' },
      { id: 'o2', date: '2026-09-01T12:00:00Z', total: '35.00', status: 'Cancelado' },
    ]);

    const headers = Array.from(el.querySelectorAll('th')).map((th) => th.textContent?.trim());
    expect(headers).toEqual(['Fecha', 'Total', 'Estado']);
    const rows = Array.from(el.querySelectorAll('tbody tr'));
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('05/10/2026');
    expect(rows[0].textContent).toContain('120.50');
    expect(rows[0].textContent).toContain('Entregado');
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });
});
