import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';

import { PurchaseApiError } from '../../models/purchase';
import { ReceiptApiError, ReceptionForm } from '../../models/receipt';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { ReceiptsApiService } from '../../services/receipts-api.service';
import { makeConfirmedPurchase } from '../../testing/purchase-fixtures';
import { makeFormLine, makeReceipt, makeReceptionForm } from '../../testing/receipt-fixtures';
import { ReceptionFormComponent } from './reception-form.component';

describe('ReceptionFormComponent', () => {
  let fixture: ComponentFixture<ReceptionFormComponent>;
  let component: ReceptionFormComponent;
  let purchasesApi: jasmine.SpyObj<PurchasesApiService>;
  let receiptsApi: jasmine.SpyObj<ReceiptsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  async function setup(form: ReceptionForm | ReceiptApiError = makeReceptionForm()): Promise<void> {
    purchasesApi = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['get']);
    purchasesApi.get.and.returnValue(of(makeConfirmedPurchase()));
    receiptsApi = jasmine.createSpyObj<ReceiptsApiService>('ReceiptsApiService', ['receptionForm', 'create']);
    receiptsApi.receptionForm.and.returnValue(form instanceof ReceiptApiError ? throwError(() => form) : of(form));
    receiptsApi.create.and.returnValue(of(makeReceipt()));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [ReceptionFormComponent],
      providers: [
        provideRouter([]),
        { provide: PurchasesApiService, useValue: purchasesApi },
        { provide: ReceiptsApiService, useValue: receiptsApi },
        { provide: ToastrService, useValue: toastr },
        { provide: ActivatedRoute, useValue: { snapshot: { paramMap: convertToParamMap({ id: 'c-1' }) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(ReceptionFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const byId = (id: string): HTMLElement | null => root().querySelector<HTMLElement>(`[data-testid="${id}"]`);
  const all = (id: string): HTMLElement[] => Array.from(root().querySelectorAll<HTMLElement>(`[data-testid="${id}"]`));
  const text = (): string => root().textContent ?? '';
  const type = (row: number, value: string): void => {
    component.quantities.at(row).setValue(value);
    fixture.detectChanges();
  };
  const reviewButton = (): HTMLButtonElement => byId('review') as HTMLButtonElement;
  const inventoryForm = (overrides: Partial<ReceptionForm> = {}): ReceptionForm =>
    makeReceptionForm({
      inventoryEnabled: true,
      warehouses: [{ id: 'w-1', name: 'Central', isDefault: true }],
      warehouseId: 'w-1',
      lines: [makeFormLine({ tracksStock: true }), makeFormLine({ itemId: 'i-2', productName: 'Bolsa', unitAbbreviation: 'u', allowsFractions: false, pending: '4.000', received: '0.000', ordered: '4.000' })],
      ...overrides,
    });

  it('lists every line read-only with bought, received and pending, and today as the date (AC-20)', async () => {
    await setup();
    expect(all('line').length).toBe(2);
    const first = all('line')[0].textContent ?? '';
    for (const expected of ['Harina', 'kg', '10.000', '4.000', '6.000']) expect(first).toContain(expected);
    expect(all('quantity').length).toBe(2);
    expect((byId('receipt-date') as HTMLInputElement).value).toBe(component.today);
    expect(byId('warehouse-block')).toBeNull();
    expect(reviewButton().disabled).toBeTrue();
    expect(byId('positive-hint')).not.toBeNull();
  });

  it('does not let the quantity exceed the pending or be invalid, and says why (AC-20)', async () => {
    await setup();
    for (const [value, message] of [['7', 'pendiente (6.000)'], ['-1', 'negativa'], ['abc', 'número válido'], ['1.0001', '3 decimales']] as const) {
      type(0, value);
      expect(byId('line-error')?.textContent).withContext(value).toContain(message);
      expect(reviewButton().disabled).withContext(value).toBeTrue();
    }
    type(1, '1.5');
    type(0, '');
    expect(byId('line-error')?.textContent).toContain('no admite fracciones');
    type(1, '2');
    expect(byId('line-error')).toBeNull();
    expect(reviewButton().disabled).toBeFalse();
  });

  it('needs at least one positive quantity; empty and zero lines are ignored (AC-20)', async () => {
    await setup();
    type(0, '0');
    expect(reviewButton().disabled).toBeTrue();
    type(1, '4');
    expect(reviewButton().disabled).toBeFalse();
  });

  it('fills the pending of the open lines and skips the complete ones (AC-20)', async () => {
    await setup(makeReceptionForm({ lines: [makeFormLine(), makeFormLine({ itemId: 'i-2', productName: 'Bolsa', pending: '0.000', received: '4.000' })] }));
    expect(byId('complete')?.textContent).toContain('Completa');
    byId('fill-all')?.click();
    fixture.detectChanges();
    expect(component.quantities.at(0).value).toBe('6.000');
    expect(component.quantities.at(1).value).toBe('');
    expect(reviewButton().disabled).toBeFalse();
  });

  it('rejects an empty or future date (AC-20)', async () => {
    await setup();
    type(0, '1');
    component.form.controls.receiptDate.setValue('2999-01-01');
    fixture.detectChanges();
    expect(byId('date-error')?.textContent).toContain('no puede ser futura');
    expect(reviewButton().disabled).toBeTrue();
    component.form.controls.receiptDate.setValue('');
    fixture.detectChanges();
    expect(byId('date-error')?.textContent).toContain('obligatoria');
  });

  it('reviews only the lines being received with what stays pending, and sends only those (AC-22)', async () => {
    await setup();
    type(0, '4');
    type(1, '0');
    reviewButton().click();
    fixture.detectChanges();
    expect(byId('review-step')).not.toBeNull();
    expect(all('review-line').length).toBe(1);
    const row = all('review-line')[0].textContent ?? '';
    for (const expected of ['Harina', '4.000', '2.000']) expect(row).toContain(expected);
    expect(byId('summary-count')?.textContent).toContain('1');
    expect(byId('stock-notice')).toBeNull();
    (byId('confirm') as HTMLButtonElement).click();
    expect(receiptsApi.create).toHaveBeenCalledTimes(1);
    const [purchaseId, input] = receiptsApi.create.calls.mostRecent().args;
    expect(purchaseId).toBe('c-1');
    expect(input).toEqual(jasmine.objectContaining({ receiptDate: component.today, warehouseId: null, lines: [{ itemId: 'i-1', quantity: '4.000' }] }));
    expect(input.receiptId).toMatch(/^[0-9a-f-]{36}$/);
  });

  it('goes back to editing without losing what was typed (AC-22)', async () => {
    await setup();
    type(0, '4');
    reviewButton().click();
    fixture.detectChanges();
    (byId('back') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(byId('edit-step')).not.toBeNull();
    expect(component.quantities.at(0).value).toBe('4');
  });

  it('after confirming it shows the toast and returns to the Receptions tab (AC-23)', async () => {
    await setup();
    type(0, '4');
    reviewButton().click();
    fixture.detectChanges();
    (byId('confirm') as HTMLButtonElement).click();
    expect(toastr.success).toHaveBeenCalledWith('Recepción REC-1A2B3C4D registrada');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases', 'c-1'], { queryParams: { tab: 'receptions' } });
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('asks before leaving with quantities typed (AC-22)', async () => {
    await setup();
    expect(component.hasUnsavedChanges()).toBeFalse();
    type(0, '1');
    expect(component.hasUnsavedChanges()).toBeTrue();
  });

  it('shows the warehouse only with Inventory and controlled products pending, preselected and required (AC-21)', async () => {
    await setup(inventoryForm());
    expect(byId('warehouse-block')).not.toBeNull();
    expect((byId('warehouse') as HTMLSelectElement).value).toBe('w-1');
    type(0, '2');
    component.form.controls.warehouseId.setValue('');
    fixture.detectChanges();
    expect(byId('warehouse-error')?.textContent).toContain('almacén');
    expect(reviewButton().disabled).toBeTrue();
    component.form.controls.warehouseId.setValue('w-1');
    fixture.detectChanges();
    expect(reviewButton().disabled).toBeFalse();
    reviewButton().click();
    fixture.detectChanges();
    expect(byId('summary-warehouse')?.textContent).toContain('Central');
    expect(byId('stock-notice')?.textContent).toContain('Central');
    (byId('confirm') as HTMLButtonElement).click();
    expect(receiptsApi.create.calls.mostRecent().args[1].warehouseId).toBe('w-1');
  });

  it('does not require the warehouse when only uncontrolled products are received (AC-21)', async () => {
    await setup(inventoryForm());
    type(1, '2');
    component.form.controls.warehouseId.setValue('');
    fixture.detectChanges();
    expect(byId('warehouse-error')).toBeNull();
    expect(reviewButton().disabled).toBeFalse();
    reviewButton().click();
    fixture.detectChanges();
    expect(byId('summary-warehouse')).toBeNull();
    (byId('confirm') as HTMLButtonElement).click();
    expect(receiptsApi.create.calls.mostRecent().args[1].warehouseId).toBeNull();
  });

  it('hides the warehouse when Inventory is on but nothing controlled is pending (AC-21)', async () => {
    await setup(inventoryForm({ lines: [makeFormLine({ tracksStock: true, pending: '0.000' }), makeFormLine({ itemId: 'i-2', pending: '2.000' })] }));
    expect(byId('warehouse-block')).toBeNull();
  });

  it('explains when there are no active warehouses and blocks the controlled lines (AC-21)', async () => {
    await setup(inventoryForm({ warehouses: [], warehouseId: null }));
    expect(byId('no-warehouses')?.textContent).toContain('No hay almacenes activos');
    type(0, '2');
    expect(reviewButton().disabled).toBeTrue();
    type(0, '');
    type(1, '2');
    expect(reviewButton().disabled).toBeFalse();
  });

  it('maps a 400 to the line and returns to editing without clearing the form (AC-22)', async () => {
    await setup();
    type(0, '4');
    type(1, '2');
    reviewButton().click();
    fixture.detectChanges();
    receiptsApi.create.and.returnValue(
      throwError(() => new ReceiptApiError('Revisa los datos ingresados.', 400, { lines: [{}, { quantity: 'No puede superar el pendiente (1.000).' }] })),
    );
    (byId('confirm') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(byId('edit-step')).not.toBeNull();
    expect(byId('line-error')?.textContent).toContain('pendiente (1.000)');
    expect(all('line')[1].className).toContain('table-warning');
    expect(component.quantities.at(0).value).toBe('4');
    expect(component.submitting).toBeFalse();
  });

  it('keeps what was typed on a 409 and re-reads the pending quantities (AC-22)', async () => {
    await setup();
    type(0, '4');
    reviewButton().click();
    fixture.detectChanges();
    receiptsApi.create.and.returnValue(throwError(() => new ReceiptApiError('Solo una compra confirmada admite recepciones.', 409)));
    receiptsApi.receptionForm.and.returnValue(of(makeReceptionForm({ lines: [makeFormLine({ pending: '3.000', received: '7.000' }), makeFormLine({ itemId: 'i-2', pending: '4.000' })] })));
    (byId('confirm') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(byId('conflict')?.textContent).toContain('confirmada');
    expect(receiptsApi.receptionForm).toHaveBeenCalledTimes(2);
    expect(component.quantities.at(0).value).toBe('4');
    expect(all('pending')[0].textContent).toContain('3.000');
    expect(byId('line-error')?.textContent).toContain('pendiente (3.000)');
  });

  it('shows a load error with a way back to the purchase', async () => {
    await setup(new ReceiptApiError('Solo una compra confirmada admite recepciones.', 409));
    expect(byId('load-error')?.textContent).toContain('confirmada');
    expect(text()).toContain('Volver a la compra');
    const failure = new PurchaseApiError('Compra no encontrada.', 404);
    expect(failure.status).toBe(404);
  });
});
