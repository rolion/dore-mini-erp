import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { StockOutput } from '../../models/order';
import { StockOutputCardComponent } from './stock-output-card.component';

const OUTPUT: StockOutput = {
  reference: 'P-1A2B3C4D',
  warehouseId: 'w-1',
  warehouseName: 'Central',
  occurredAt: '2026-10-03T15:30:00Z',
  userName: 'ana',
  movements: [
    { id: 'm-1', productId: 'p-1', productName: 'Bolsas', quantity: '4.0000', unit: 'u' },
    { id: 'm-2', productId: 'p-2', productName: 'Harina', quantity: '2.5000', unit: 'kg' },
  ],
};

describe('StockOutputCardComponent', () => {
  let fixture: ComponentFixture<StockOutputCardComponent>;

  beforeEach(() => {
    TestBed.configureTestingModule({ imports: [StockOutputCardComponent], providers: [provideRouter([])] });
    fixture = TestBed.createComponent(StockOutputCardComponent);
    fixture.componentRef.setInput('orderId', 'o-1');
    fixture.componentRef.setInput('output', OUTPUT);
    fixture.detectChanges();
  });

  function el(): HTMLElement {
    return fixture.nativeElement as HTMLElement;
  }

  it('shows reference, warehouse, date and the linked movements (UI-05, AC-12)', () => {
    const text = (id: string) => el().querySelector(`[data-testid="${id}"]`)?.textContent?.trim();
    expect(text('output-reference')).toBe('P-1A2B3C4D');
    expect(text('output-warehouse')).toBe('Central');
    expect(text('output-date')).toMatch(/^\d{2}\/\d{2}\/2026 \d{2}:\d{2}$/);
    const rows = Array.from(el().querySelectorAll('[data-testid="output-row"]')).map((row) =>
      Array.from(row.querySelectorAll('td')).map((td) => td.textContent?.trim()),
    );
    expect(rows).toEqual([['Bolsas', '4', 'u'], ['Harina', '2.5', 'kg']]);
  });

  it('links to the movements filtered by the order (UI-05, AC-12)', () => {
    const link = el().querySelector('[data-testid="view-movements"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/movements?source_type=sales_order&source_id=o-1');
  });
});
