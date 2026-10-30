import { NgbModal, NgbModalRef } from '@ng-bootstrap/ng-bootstrap';
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
      movements: [{ id: 'm-1', reference: 'REC-1A2B3C4D', productName: 'Harina', warehouseName: 'Central', quantity: '4.000', unitAbbreviation: 'kg', status: 'confirmed', reversedBy: null }],
      inventoryMode: 'inventory',
      inventoryAvailable: true,
    }));
    expect(byId('warehouse')?.textContent).toContain('Central');
    expect(all('movement')[0].textContent).toContain('4.000');
    expect(all('movement')[0].textContent).toContain('REC-1A2B3C4D');
    expect(byId('view-movements')?.getAttribute('href')).toBe('/pocketbiz/inventory/movements?source_type=purchase_receipt&source_id=r-1');
  });

  it('says a documentary receipt did not move stock when Inventory is on (AC-24)', async () => {
    await setup(makeReceipt({ movements: [] }));
    expect(byId('no-movements')?.textContent).toContain('no movió existencias');
    expect(byId('view-movements')).toBeNull();
  });

  it('keeps the movements without a link when Inventory was turned off later (AC-13)', async () => {
    await setup(makeReceipt({
      warehouse: { id: 'w-1', name: 'Central' },
      inventoryMode: 'inventory',
      inventoryAvailable: false,
      movements: [{ id: 'm-1', reference: 'REC-1A2B3C4D', productName: 'Harina', warehouseName: 'Central', quantity: '4.000', unitAbbreviation: 'kg', status: 'confirmed', reversedBy: null }],
    }));
    expect(all('movement').length).toBe(1);
    expect(byId('view-movements')).toBeNull();
    expect(byId('movements-disabled')?.textContent).toContain('deshabilitado');
  });

  it('says a documentary receipt had no inventory movement, and keeps saying it (AC-14)', async () => {
    await setup(makeReceipt({ inventoryMode: 'documental', inventoryAvailable: true, movements: null }));
    expect(byId('documental-note')?.textContent).toContain('Recepción documental, sin movimiento de inventario');
    expect(byId('no-movements')).toBeNull(); // un solo mensaje
    expect(byId('view-movements')).toBeNull();
  });

  it('says an inventory-mode receipt generated no entries, and flags lines without stock control (AC-13, AC-14)', async () => {
    await setup(makeReceipt({
      inventoryMode: 'inventory',
      inventoryAvailable: true,
      movements: [],
      lines: [{ itemId: 'i-1', productId: 'p-1', productName: 'Bolsa', unitAbbreviation: 'u', quantity: '2.000', stockEntry: false }],
    }));
    expect(byId('no-movements')?.textContent).toContain('no generó entradas de inventario');
    expect(byId('no-entry')?.textContent).toContain('Sin control de stock · sin entrada');
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

  it('offers «Revertir recepción» only when the server allows it (AC-16)', async () => {
    await setup(makeReceipt({ canRevert: true }));
    expect(byId('revert')).not.toBeNull();
    expect(byId('revert-blocked')).toBeNull();
  });

  it('offers no reversal for a reverted receipt and shows the reversal data (AC-11, AC-16)', async () => {
    await setup(makeReceipt({ status: 'reverted', canRevert: false, reversal: { revertedAt: '2026-10-31T10:00:00Z', userName: 'bea', reason: 'Error de conteo' } }));
    expect(byId('revert')).toBeNull();
    expect(byId('revert-blocked')).toBeNull();
    expect(byId('status-badge')?.textContent).toContain('Revertida');
    expect(byId('reversal-user')?.textContent).toContain('bea');
    expect(byId('reversal-reason')?.textContent).toContain('Error de conteo');
    expect(byId('reversal-date')?.textContent).toContain('31/10/2026');
  });

  it('explains why a receipt that moved stock cannot be reverted while Inventory is off (AC-10)', async () => {
    await setup(makeReceipt({ canRevert: false, inventoryMode: 'inventory', inventoryAvailable: false }));
    expect(byId('revert')).toBeNull();
    expect(byId('revert-blocked')?.textContent).toContain('Inventario está deshabilitado');
  });

  it('shows the state of each movement and links its counter-movement (AC-11)', async () => {
    const base = { id: 'm-1', reference: 'REC-1', productName: 'Harina', warehouseName: 'Central', quantity: '4.000', unitAbbreviation: 'kg' };
    await setup(makeReceipt({
      inventoryMode: 'inventory', inventoryAvailable: true,
      movements: [{ ...base, status: 'reversed', reversedBy: { id: 'm-2', reference: 'REC-1' } }, { ...base, id: 'm-3', status: 'confirmed', reversedBy: null }],
    }));
    const statuses = all('movement-status').map((s) => s.textContent?.replace(/\s+/g, ' ').trim());
    expect(statuses[0]).toContain('Revertido');
    expect(statuses[1]).toBe('Confirmado');
    expect(byId('counter-link')?.getAttribute('href')).toBe('/pocketbiz/inventory/movements/m-2');
  });

  it('opens the dialog with the receipt, reloads and confirms after reverting (AC-16)', async () => {
    await setup(makeReceipt());
    const dialog = { init: jasmine.createSpy('init') };
    spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({ componentInstance: dialog, result: Promise.resolve(makeReceipt()) } as unknown as NgbModalRef);
    (byId('revert') as HTMLButtonElement).click();
    await fixture.whenStable();
    fixture.detectChanges();
    expect(dialog.init).toHaveBeenCalledWith(jasmine.objectContaining({ id: 'r-1' }));
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(byId('success')?.textContent).toContain('Recepción revertida');
  });

  it('does not reload when the dialog is dismissed', async () => {
    await setup(makeReceipt());
    spyOn(TestBed.inject(NgbModal), 'open').and.returnValue({ componentInstance: { init: () => undefined }, result: Promise.reject(undefined) } as unknown as NgbModalRef);
    (byId('revert') as HTMLButtonElement).click();
    await fixture.whenStable();
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
