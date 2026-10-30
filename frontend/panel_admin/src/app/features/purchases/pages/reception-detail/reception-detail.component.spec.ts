import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';

import { Receipt, ReceiptApiError } from '../../models/receipt';
import { ReceiptsApiService } from '../../services/receipts-api.service';
import { makeReceipt } from '../../testing/receipt-fixtures';
import { ReceptionDetailComponent } from './reception-detail.component';

describe('ReceptionDetailComponent', () => {
  let fixture: ComponentFixture<ReceptionDetailComponent>;
  let api: jasmine.SpyObj<ReceiptsApiService>;

  async function setup(receipt: Receipt | ReceiptApiError): Promise<void> {
    api = jasmine.createSpyObj<ReceiptsApiService>('ReceiptsApiService', ['get']);
    api.get.and.returnValue(receipt instanceof ReceiptApiError ? throwError(() => receipt) : of(receipt));
    await TestBed.configureTestingModule({
      imports: [ReceptionDetailComponent],
      providers: [
        provideRouter([]),
        { provide: ReceiptsApiService, useValue: api },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1', receiptId: 'r-1' }) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ReceptionDetailComponent);
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const all = (id: string): HTMLElement[] => Array.from(root().querySelectorAll<HTMLElement>(`[data-testid="${id}"]`));

  it('shows reference, purchase, date, status, user and the received products (AC-24)', async () => {
    await setup(makeReceipt());
    expect(api.get).toHaveBeenCalledWith('c-1', 'r-1');
    expect(root().textContent).toContain('REC-1A2B3C4D');
    expect(byId('status-badge')?.className).toContain('col-green');
    expect(byId('purchase-link')?.getAttribute('href')).toBe('/pocketbiz/purchases/c-1');
    expect(byId('receipt-date')?.textContent).toContain('30/10/2026');
    expect(byId('user')?.textContent).toContain('ana');
    expect(all('line')[0].textContent).toContain('Harina');
    expect(all('line')[0].textContent).toContain('4.000');
    expect(byId('back')?.getAttribute('href')).toBe('/pocketbiz/purchases/c-1?tab=receptions');
  });

  it('shows neither warehouse nor movements when Inventory is off (AC-24)', async () => {
    await setup(makeReceipt({ warehouse: null, movements: null }));
    expect(byId('warehouse')).toBeNull();
    expect(byId('no-movements')).toBeNull();
    expect(root().textContent).not.toContain('Movimientos de inventario');
  });

  it('shows the warehouse, the linked movements and the link to Movements (AC-24)', async () => {
    await setup(makeReceipt({
      warehouse: { id: 'w-1', name: 'Central' },
      movements: [{ id: 'm-1', productName: 'Harina', warehouseName: 'Central', quantity: '4.000', unitAbbreviation: 'kg' }],
    }));
    expect(byId('warehouse')?.textContent).toContain('Central');
    expect(all('movement')[0].textContent).toContain('4.000');
    expect(byId('view-movements')?.getAttribute('href')).toBe('/pocketbiz/inventory/movements?source_type=purchase_receipt&source_id=r-1');
  });

  it('says a documentary receipt did not move stock when Inventory is on (AC-24)', async () => {
    await setup(makeReceipt({ movements: [] }));
    expect(byId('no-movements')?.textContent).toContain('no movió existencias');
    expect(byId('view-movements')).toBeNull();
  });

  it('shows a reverted receipt with its status', async () => {
    await setup(makeReceipt({ status: 'reverted' }));
    expect(byId('status-badge')?.textContent).toContain('Revertida');
  });

  it('shows the error with a retry', async () => {
    await setup(new ReceiptApiError('No se encontró la compra o la recepción.', 404));
    expect(byId('error')?.textContent).toContain('No se encontró');
    api.get.and.returnValue(of(makeReceipt()));
    byId('retry')?.click();
    fixture.detectChanges();
    expect(byId('error')).toBeNull();
    expect(root().textContent).toContain('REC-1A2B3C4D');
  });
});
