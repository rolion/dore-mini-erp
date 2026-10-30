import { ComponentFixture, TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { of, throwError } from 'rxjs';

import { ReceiptApiError } from '../../models/receipt';
import { ReceiptsApiService } from '../../services/receipts-api.service';
import { makeReceipt } from '../../testing/receipt-fixtures';
import { ReceiptRevertDialogComponent } from './receipt-revert-dialog.component';

describe('ReceiptRevertDialogComponent', () => {
  let fixture: ComponentFixture<ReceiptRevertDialogComponent>;
  let component: ReceiptRevertDialogComponent;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;
  let api: jasmine.SpyObj<ReceiptsApiService>;

  async function setup(overrides: Parameters<typeof makeReceipt>[0] = {}): Promise<void> {
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    api = jasmine.createSpyObj<ReceiptsApiService>('ReceiptsApiService', ['revert']);
    await TestBed.configureTestingModule({
      imports: [ReceiptRevertDialogComponent],
      providers: [
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ReceiptsApiService, useValue: api },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ReceiptRevertDialogComponent);
    component = fixture.componentInstance;
    component.init(makeReceipt(overrides));
    fixture.detectChanges();
  }

  const el = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => el().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const type = (value: string): void => {
    component.form.controls.reason.setValue(value);
    fixture.detectChanges();
  };

  it('lists every line of the receipt, the impact and that payments are not returned (AC-16)', async () => {
    await setup({
      inventoryMode: 'inventory',
      lines: [
        { itemId: 'i-1', productId: 'p-1', productName: 'Harina', unitAbbreviation: 'kg', quantity: '4.000', stockEntry: true },
        { itemId: 'i-2', productId: 'p-2', productName: 'Bolsas', unitAbbreviation: 'u', quantity: '2.000', stockEntry: false },
      ],
    });
    const lines = Array.from(el().querySelectorAll('[data-testid="line"]')).map((l) => l.textContent?.replace(/\s+/g, ' ').trim());
    expect(lines.length).toBe(2);
    expect(lines[0]).toContain('Harina');
    expect(lines[0]).toContain('Se registrará una salida de stock');
    expect(lines[1]).toContain('Sin control de stock');
    expect(byId('impact')?.textContent).toContain('no devuelve los pagos');
    expect(byId('summary')?.textContent).toContain('no hay reversión parcial');
  });

  it('explains that a documental receipt has no inventory movements (AC-10)', async () => {
    await setup({ inventoryMode: 'documental' });
    expect(byId('documental-note')?.textContent).toContain('no hay movimientos de inventario');
    expect(byId('line')?.textContent).toContain('Sin movimiento de inventario');
  });

  it('requires a reason of at most 200 characters (AC-09)', async () => {
    await setup();
    expect((byId('revert-receipt') as HTMLButtonElement).disabled).toBeTrue();
    type('   ');
    expect((byId('revert-receipt') as HTMLButtonElement).disabled).toBeTrue();
    type('Error de conteo');
    expect((byId('revert-receipt') as HTMLButtonElement).disabled).toBeFalse();
    expect(el().querySelector('textarea')?.getAttribute('maxlength')).toBe('200');
  });

  it('sends the trimmed reason and closes with the reverted receipt (AC-06)', async () => {
    await setup();
    const reverted = makeReceipt({ status: 'reverted' });
    api.revert.and.returnValue(of(reverted));
    type('  Error de conteo ');
    component.submit();
    expect(api.revert).toHaveBeenCalledWith('c-1', 'r-1', 'Error de conteo');
    expect(activeModal.close).toHaveBeenCalledWith(reverted);
  });

  it('shows every line without stock and keeps the reason when stock is insufficient (AC-07)', async () => {
    await setup();
    const shortage = {
      warehouseName: 'Central',
      lines: [
        { productName: 'Harina', unit: 'kg', requested: '10.000', available: '2.000' },
        { productName: 'Azúcar', unit: 'kg', requested: '5.000', available: '0.000' },
      ],
    };
    api.revert.and.returnValue(throwError(() => new ReceiptApiError('x', 409, { lines: [] }, 'insufficient_stock', shortage)));
    type('Error');
    component.submit();
    fixture.detectChanges();
    expect(activeModal.close).not.toHaveBeenCalled();
    expect(byId('shortage')?.textContent).toContain('No se revirtió ninguna línea');
    const rows = Array.from(el().querySelectorAll('[data-testid="shortage-line"]')).map((r) => r.textContent?.replace(/\s+/g, ' ').trim());
    expect(rows).toEqual([
      'Harina: se necesitan 10.000 kg y hay 2.000 kg.',
      'Azúcar: se necesitan 5.000 kg y hay 0.000 kg.',
    ]);
    expect(component.form.controls.reason.value).toBe('Error');
    expect((byId('revert-receipt') as HTMLButtonElement).disabled).toBeFalse();
  });

  it('shows other conflicts and the reason error inside the dialog (AC-09, AC-10)', async () => {
    await setup();
    api.revert.and.returnValue(throwError(() => new ReceiptApiError('La recepción ya fue revertida.', 409, { lines: [] }, 'already_reverted')));
    type('Error');
    component.submit();
    fixture.detectChanges();
    expect(byId('error')?.textContent).toContain('ya fue revertida');
    api.revert.and.returnValue(throwError(() => new ReceiptApiError('x', 400, { lines: [], reason: 'El motivo es obligatorio.' })));
    component.submit();
    fixture.detectChanges();
    expect(byId('reason-error')?.textContent).toContain('obligatorio');
  });

  it('«Volver» dismisses without changes', async () => {
    await setup();
    byId('back')?.click();
    expect(activeModal.dismiss).toHaveBeenCalled();
    expect(api.revert).not.toHaveBeenCalled();
  });
});
