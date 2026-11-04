import { provideTestTranslations } from '../../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { CustomerOrderSummary } from '../../models/customer';
import { CustomerPurchaseHistoryComponent } from './customer-purchase-history.component';

describe('CustomerPurchaseHistoryComponent', () => {
  beforeEach(() => TestBed.configureTestingModule({ providers: [...provideTestTranslations(), provideRouter([])] }));

  function render(
    inputs: Partial<{
      orders: CustomerOrderSummary[];
      loading: boolean;
      error: string;
      total: number;
      customerId: string;
      customerName: string;
      ordersEnabled: boolean;
      canCreateOrder: boolean;
    }> = {},
  ): HTMLElement {
    const fixture = TestBed.createComponent(CustomerPurchaseHistoryComponent);
    for (const [name, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(name, value);
    }
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  const ORDERS: CustomerOrderSummary[] = [
    {
      id: 'o1', code: 'A-0042', date: '2026-10-05', total: '120.50', paidTotal: '100.00', balance: '20.50',
      status: 'DELIVERED', paymentStatus: 'PARTIAL',
    },
    {
      id: 'o2', code: 'A-0031', date: '2026-09-01', total: '35.00', paidTotal: '0.00', balance: '35.00',
      status: 'CANCELLED', paymentStatus: 'PENDING',
    },
  ];

  it('shows the empty message when there are no orders (AC-06)', () => {
    const el = render();
    expect(el.textContent).toContain('Historial de compras');
    expect(el.textContent).toContain('Este cliente aún no tiene pedidos.');
    expect(el.querySelector('table')).toBeNull();
  });

  it('offers to create the first order of an active customer, with the customer preselected (AC-06, AC-07)', () => {
    const el = render({ canCreateOrder: true, customerId: 'c-1', customerName: 'Ana Pérez' });
    const link = el.querySelector('[data-testid="history-create-first"]') as HTMLAnchorElement;
    expect(link.textContent?.trim()).toBe('Crear primer pedido');
    expect(link.getAttribute('href')).toBe('/pocketbiz/sales/orders/new?customer=c-1&customer_name=Ana%20P%C3%A9rez');
  });

  it('does not offer to create an order when it is not possible (AC-07)', () => {
    expect(render({ canCreateOrder: false }).querySelector('[data-testid="history-create-first"]')).toBeNull();
  });

  it('lists code, date, total, paid, balance and both statuses of each order (AC-04)', () => {
    const el = render({ orders: ORDERS, total: 2 });

    const headers = Array.from(el.querySelectorAll('th')).map((th) => th.textContent?.trim());
    expect(headers).toEqual(['Pedido', 'Fecha', 'Total', 'Pagado', 'Saldo', 'Entrega', 'Pago']);
    const rows = Array.from(el.querySelectorAll('tbody tr')).map((row) =>
      Array.from(row.querySelectorAll('td')).map((cell) => cell.textContent?.trim()),
    );
    expect(rows[0].slice(0, 5)).toEqual(['A-0042', '05/10/2026', 'Bs 120.50', 'Bs 100.00', 'Bs 20.50']);
    expect(rows[0][5]).toContain('Entregado');
    expect(rows[0][6]).toContain('Parcial');
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });

  it('mutes cancelled orders and hides their balance (AC-04)', () => {
    const el = render({ orders: ORDERS, total: 2 });
    const cancelled = el.querySelectorAll('tbody tr')[1];
    expect(cancelled.classList).toContain('text-muted');
    expect(cancelled.querySelectorAll('td')[4].textContent?.trim()).toBe('—');
    expect(cancelled.querySelectorAll('td')[5].textContent).toContain('Cancelado');
  });

  it('links each order code to its detail page (AC-04)', () => {
    const el = render({ orders: ORDERS });
    const hrefs = Array.from(el.querySelectorAll('tbody a')).map((a) => a.getAttribute('href'));
    expect(hrefs).toEqual(['/pocketbiz/sales/orders/o1', '/pocketbiz/sales/orders/o2']);
  });

  it('shows unknown status codes as they come instead of failing (EDGE-05)', () => {
    const el = render({ orders: [{ ...ORDERS[0], status: 'FUTURE', paymentStatus: 'OTHER' }] });
    expect(el.querySelector('tbody')?.textContent).toContain('FUTURE');
    expect(el.querySelector('tbody')?.textContent).toContain('OTHER');
  });

  it('says how many orders are shown out of the total (AC-05)', () => {
    expect(render({ orders: ORDERS, total: 2 }).querySelector('[data-testid="history-count"]')?.textContent)
      .toContain('Pedidos mostrados: 2 de 2.');
    expect(render({ orders: ORDERS, total: 250 }).querySelector('[data-testid="history-count"]')?.textContent)
      .toContain('Pedidos mostrados: 2 de 250.');
  });

  it('links to the order list filtered by this customer (AC-05)', () => {
    const el = render({ orders: ORDERS, customerId: 'c-1', customerName: 'Ana' });
    const link = el.querySelector('[data-testid="history-all-orders"]') as HTMLAnchorElement;
    expect(link.textContent?.trim()).toBe('Ver todos los pedidos');
    expect(link.getAttribute('href')).toBe('/pocketbiz/sales/orders?customer=c-1&customer_name=Ana');
  });

  it('hides the order list link when the Orders module is disabled or there are no orders (AC-05)', () => {
    expect(render({ orders: ORDERS, ordersEnabled: false }).querySelector('[data-testid="history-all-orders"]')).toBeNull();
    expect(render({}).querySelector('[data-testid="history-all-orders"]')).toBeNull();
  });

  it('makes the table readable by assistive technology (AC-09)', () => {
    const el = render({ orders: ORDERS, customerName: 'Ana' });
    expect(el.querySelector('caption')?.textContent?.trim()).toBe('Historial de compras de Ana');
    expect(Array.from(el.querySelectorAll('th')).every((th) => th.getAttribute('scope') === 'col')).toBeTrue();
  });

  it('shows a loading message and hides the empty message meanwhile (AC-03)', () => {
    const el = render({ loading: true });
    expect(el.querySelector('[data-testid="history-loading"]')).not.toBeNull();
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });

  it('shows the error instead of the table or the empty message (EDGE-01)', () => {
    const el = render({ error: 'No se pudo cargar el historial de compras.', orders: ORDERS });
    expect(el.querySelector('[data-testid="history-error"]')?.textContent).toContain('No se pudo cargar');
    expect(el.querySelector('table')).toBeNull();
    expect(el.textContent).not.toContain('Este cliente aún no tiene pedidos.');
  });
});
