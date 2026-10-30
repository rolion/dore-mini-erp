import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { ReceiptApiError } from '../../models/receipt';
import { ReceiptsApiService } from '../../services/receipts-api.service';
import { makeCancelledPurchase, makeConfirmedPurchase, makePurchaseItem } from '../../testing/purchase-fixtures';
import { makeReceiptSummary } from '../../testing/receipt-fixtures';
import { PurchaseReceiptsTabComponent } from './purchase-receipts-tab.component';

describe('PurchaseReceiptsTabComponent', () => {
  let fixture: ComponentFixture<PurchaseReceiptsTabComponent>;
  let api: jasmine.SpyObj<ReceiptsApiService>;

  async function setup(purchase = makeConfirmedPurchase(), list = of({ count: 0, next: null, previous: null, results: [] as ReturnType<typeof makeReceiptSummary>[] })): Promise<void> {
    api = jasmine.createSpyObj<ReceiptsApiService>('ReceiptsApiService', ['list']);
    api.list.and.returnValue(list);
    await TestBed.configureTestingModule({
      imports: [PurchaseReceiptsTabComponent],
      providers: [provideRouter([]), { provide: ReceiptsApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(PurchaseReceiptsTabComponent);
    fixture.componentRef.setInput('purchase', purchase);
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const all = (id: string): HTMLElement[] => Array.from(root().querySelectorAll<HTMLElement>(`[data-testid="${id}"]`));

  it('explains the empty state of a confirmed purchase and offers to register one (AC-18, AC-19)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith('c-1');
    expect(byId('empty')?.textContent).toContain('Aún no hay recepciones registradas');
    expect(byId('register')?.getAttribute('href')).toBe('/pocketbiz/purchases/c-1/receipts/new');
    expect(byId('reception-status')?.textContent).toContain('Sin recibir');
  });

  it('shows the progress by product and the registered receipts with their status and user (AC-18)', async () => {
    const purchase = makeConfirmedPurchase({
      receptionStatus: 'partial',
      items: [makePurchaseItem({ receivedQuantity: '1.000', pendingQuantity: '1.500' })],
    });
    await setup(purchase, of({ count: 2, next: null, previous: null, results: [makeReceiptSummary(), makeReceiptSummary({ id: 'r-2', reference: 'REC-2', status: 'reverted', userName: '' })] }));
    const cells = all('progress-row')[0].textContent ?? '';
    for (const expected of ['Harina', '2.500', '1.000', '1.500']) expect(cells).toContain(expected);
    expect(byId('reception-status')?.textContent).toContain('Recibida parcialmente');
    const rows = all('receipt-row');
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain('REC-1A2B3C4D');
    expect(rows[0].textContent).toContain('30/10/2026');
    expect(rows[0].textContent).toContain('Confirmada');
    expect(rows[0].textContent).toContain('ana');
    expect(rows[1].textContent).toContain('Revertida');
    expect(all('receipt-link')[0].getAttribute('href')).toBe('/pocketbiz/purchases/c-1/receipts/r-1');
  });

  it('does not offer to register when the server does not allow it and says it is fully received (AC-19)', async () => {
    await setup(makeConfirmedPurchase({ allowedActions: [], receptionStatus: 'received' }));
    expect(byId('register')).toBeNull();
    expect(byId('fully-received')).not.toBeNull();
  });

  it('shows no progress and a different explanation for a cancelled purchase (AC-18)', async () => {
    await setup(makeCancelledPurchase());
    expect(byId('progress-row')).toBeNull();
    expect(byId('empty')?.textContent).toContain('cuando la compra está confirmada');
    expect(byId('register')).toBeNull();
  });

  it('shows the server error with a retry', async () => {
    await setup(makeConfirmedPurchase(), throwError(() => new ReceiptApiError('Sin conexión.', 0)));
    expect(byId('error')?.textContent).toContain('Sin conexión.');
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [makeReceiptSummary()] }));
    byId('retry')?.click();
    fixture.detectChanges();
    expect(all('receipt-row').length).toBe(1);
  });
});
