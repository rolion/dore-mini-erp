import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CustomerOrderSummary } from '../../models/customer';
import { CustomerPurchaseHistoryComponent } from './customer-purchase-history.component';

describe('CustomerPurchaseHistoryComponent', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [provideRouter([])] }));

  function render(
    inputs: Partial<{ orders: CustomerOrderSummary[]; loading: boolean; error: string; total: number }> = {},
  ): HTMLElement {
    const fixture = TestBed.createComponent(CustomerPurchaseHistoryComponent);
    for (const [name, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(name, value);
    }
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const ORDERS: CustomerOrderSummary[] = [
    { id: 'o1', date: '2026-10-05', total: '120.50', status: 'DELIVERED', paymentStatus: 'PARTIAL' },
    { id: 'o2', date: '2026-09-01', total: '35.00', status: 'CANCELLED', paymentStatus: 'PENDING' },
  ];

  it('shows the empty message when there are no orders (AC-26)', () => {
    const el = render();
    expect(el.textContent).toContain('Historial de compras');
    expect(el.textContent).toContain('Este cliente aún no tiene pedidos.');
    expect(el.querySelector('table')).toBeNull();
  });

  it('lists date, total, delivery status and payment status of each order (AC-26)', () => {
    const el = render({ orders: ORDERS, total: 2 });

    const headers = Array.from(el.querySelectorAll('th')).map((th) => th.textContent?.trim());
    expect(headers).toEqual(['Fecha', 'Total', 'Estado', 'Pago']);
    const rows = Array.from(el.querySelectorAll('tbody tr')).map((row) =>
      Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim()),
    );
    expect(rows).toEqual([
      ['05/10/2026', 'Bs 120.50', 'Entregado', 'Parcial'],
      ['01/09/2026', 'Bs 35.00', 'Cancelado', 'Pendiente'],
    ]);
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
    expect(el.querySelector('[data-testid="history-partial"]')).toBeNull();
  });

  it('links each order date to its detail page (AC-26)', () => {
    const el = render({ orders: ORDERS });
    const hrefs = Array.from(el.querySelectorAll('tbody a')).map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(['/sales/orders/o1', '/sales/orders/o2']);
  });

  it('shows unknown status codes as they come instead of failing (AC-26)', () => {
    const el = render({ orders: [{ ...ORDERS[0], status: 'FUTURE', paymentStatus: 'OTHER' }] });
    expect(el.querySelector('tbody')?.textContent).toContain('FUTURE');
    expect(el.querySelector('tbody')?.textContent).toContain('OTHER');
  });

  it('says when only the most recent orders are shown (AC-26)', () => {
    const el = render({ orders: ORDERS, total: 250 });
    expect(el.querySelector('[data-testid="history-partial"]')?.textContent).toContain('2 pedidos más recientes de 250');
  });

  it('shows a loading message and hides the empty message meanwhile (AC-26)', () => {
    const el = render({ loading: true });
    expect(el.querySelector('[data-testid="history-loading"]')).not.toBeNull();
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });

  it('shows the error instead of the table or the empty message (AC-26)', () => {
    const el = render({ error: 'No se pudo cargar el historial de compras.', orders: ORDERS });
    expect(el.querySelector('[data-testid="history-error"]')?.textContent).toContain('No se pudo cargar');
    expect(el.querySelector('table')).toBeNull();
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });
});
