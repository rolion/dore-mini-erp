import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';
import { AdjustmentBalance, StockAdjustmentDetail } from '../../models/adjustment';
import { InventoryApiError } from '../../models/api-error';
import { OpeningProduct } from '../../models/stock';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';
import { OpeningProductsService } from '../../services/opening-products.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeAdjustmentDetail } from '../../testing/adjustment-fixtures';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { AdjustmentFormComponent, NO_DIFFERENCE_MESSAGE } from './adjustment-form.component';

const PIECE: OpeningProduct = { id: 'p-1', name: 'Harina', unit: { abbreviation: 'u', allowsFractions: false } };
const BALANCE: AdjustmentBalance = { systemQuantity: '10.0000', unit: { abbreviation: 'u', allowsFractions: false } };

describe('AdjustmentFormComponent', () => {
  let fixture: ComponentFixture<AdjustmentFormComponent>;
  let component: AdjustmentFormComponent;
  let api: jasmine.SpyObj<AdjustmentsApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  beforeEach(async () => {
    api = jasmine.createSpyObj<AdjustmentsApiService>('AdjustmentsApiService', ['balance', 'confirm']);
    api.balance.and.returnValue(of(BALANCE));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [makeWarehouse()] }));
    const products = jasmine.createSpyObj<OpeningProductsService>('OpeningProductsService', ['search']);
    products.search.and.returnValue(of([PIECE]));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [AdjustmentFormComponent],
      providers: [
        provideRouter([]),
        { provide: AdjustmentsApiService, useValue: api },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: OpeningProductsService, useValue: products },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(AdjustmentFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const text = (testId: string) => el().querySelector(`[data-testid="${testId}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';

  function fill(counted: string, reason = 'Conteo físico'): void {
    component.form.controls.product.setValue(PIECE);
    component.form.controls.countedQuantity.setValue(counted);
    component.form.controls.reason.setValue(reason);
    component.form.markAsDirty();
    component.form.controls.countedQuantity.markAsDirty();
    component.form.controls.reason.markAsDirty();
    fixture.detectChanges();
  }

  function goToReview(counted = '7'): void {
    fill(counted);
    component.review();
    fixture.detectChanges();
  }

  it('starts with the default warehouse and nothing to lose (UI-02)', () => {
    expect(component.form.controls.warehouseId.value).toBe('w-1');
    expect(component.hasUnsavedChanges()).toBeFalse();
    expect((el().querySelector('[data-testid="review"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows the current balance read-only once product and warehouse are chosen (AC-01)', () => {
    fill('7');
    expect(api.balance).toHaveBeenCalledWith('p-1', 'w-1');
    const input = el().querySelector('[data-testid="balance"]') as HTMLInputElement;
    expect(input.readOnly).toBeTrue();
    expect(input.value).toBe('10 u');
  });

  it('calculates the difference and the direction (AC-01)', () => {
    fill('7');
    expect(text('difference-preview')).toBe('Diferencia: -3 u · Salida de ajuste');
    fill('12');
    expect(text('difference-preview')).toBe('Diferencia: +2 u · Entrada de ajuste');
  });

  it('says «Sin diferencia» and does not allow confirming when the count equals the balance (AC-04)', () => {
    fill('10');
    expect(text('no-difference')).toBe(NO_DIFFERENCE_MESSAGE);
    expect(component.canReview).toBeFalse();
  });

  it('requires a reason, a valid non-negative quantity and a unit-compatible quantity (AC-01)', () => {
    fill('7', '   ');
    expect(component.canReview).toBeFalse();
    expect(component.reasonMessage).toBe('El motivo es obligatorio.');
    for (const bad of ['', '-1', 'abc', '1.5']) {
      fill(bad);
      expect(component.canReview).withContext(bad).toBeFalse();
    }
    fill('0');
    expect(component.canReview).toBeTrue();
  });

  it('summarises the adjustment before confirming (UI-02)', () => {
    goToReview('7');
    expect(text('summary-product')).toBe('Harina');
    expect(text('summary-balance')).toBe('10 u');
    expect(text('summary-counted')).toBe('7 u');
    expect(text('summary-difference')).toBe('-3 u · Salida de ajuste');
    component.backToEdit();
    expect(component.step).toBe('edit');
  });

  it('confirms with the expected balance and the idempotency key, then opens the detail (AC-02)', () => {
    api.confirm.and.returnValue(of(makeAdjustmentDetail()));
    goToReview('7');
    component.confirm();
    const input = api.confirm.calls.mostRecent().args[0];
    expect(input).toEqual(
      jasmine.objectContaining({
        productId: 'p-1',
        warehouseId: 'w-1',
        countedQuantity: '7',
        expectedSystemQuantity: '10.0000',
        reason: 'Conteo físico',
      }),
    );
    expect(input.adjustmentId).toMatch(/^[0-9a-f-]{36}$/);
    expect(toastr.success).toHaveBeenCalledWith('Ajuste registrado');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/adjustments', 'a-1']);
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('ignores a second click while the request is in flight (AC-07)', () => {
    const pending = new Subject<StockAdjustmentDetail>();
    api.confirm.and.returnValue(pending);
    goToReview('7');
    component.confirm();
    component.confirm();
    expect(api.confirm).toHaveBeenCalledTimes(1);
    expect(component.saving).toBeTrue();
  });

  it('shows the new balance and requires reconfirming when it changed (AC-03)', () => {
    api.confirm.and.returnValues(
      throwError(() => new InventoryApiError('El saldo cambió', 409, {}, 'balance_changed', [], [], '8.0000')),
      of(makeAdjustmentDetail()),
    );
    goToReview('7');
    component.confirm();
    fixture.detectChanges();
    expect(component.step).toBe('review');
    expect(api.confirm).toHaveBeenCalledTimes(1); // no se reenvía solo
    expect(text('balance-notice')).toContain('de 10 a 8');
    expect(text('balance-notice')).toContain('-1 u');
    expect(text('summary-balance')).toBe('8 u');
    const firstKey = api.confirm.calls.mostRecent().args[0].adjustmentId;
    component.confirm();
    const second = api.confirm.calls.mostRecent().args[0];
    expect(second.expectedSystemQuantity).toBe('8.0000');
    expect(second.adjustmentId).toBe(firstKey);
  });

  it('keeps the warning and info notices readable with dark text (REV-03)', () => {
    api.confirm.and.returnValue(
      throwError(() => new InventoryApiError('El saldo cambió', 409, {}, 'balance_changed', [], [], '8.0000')),
    );
    goToReview('7');
    component.confirm();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="balance-notice"]')?.classList).toContain('text-dark');
    component.form.controls.countedQuantity.setValue('8'); // igual al saldo vigente (8)
    component.step = 'edit';
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="no-difference"]')?.classList).toContain('text-dark');
  });

  it('reports «Sin diferencia» when the new balance equals the count and blocks confirming (AC-03, AC-04)', () => {
    api.confirm.and.returnValue(
      throwError(() => new InventoryApiError('El saldo cambió', 409, {}, 'balance_changed', [], [], '7.0000')),
    );
    goToReview('7');
    component.confirm();
    fixture.detectChanges();
    expect(text('no-difference')).toBe(NO_DIFFERENCE_MESSAGE);
    expect((el().querySelector('[data-testid="confirm"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows product, warehouse, requested and available on insufficient stock and keeps the form (AC-06)', () => {
    const info = { productName: 'Harina', warehouseName: 'Central', requested: '3.000', available: '2.000', unit: 'u' };
    api.confirm.and.returnValue(
      throwError(() => new InventoryApiError('Sin saldo', 409, {}, 'insufficient_stock', [], [], null, info)),
    );
    goToReview('7');
    component.confirm();
    fixture.detectChanges();
    expect(component.step).toBe('edit');
    expect(text('stock-product')).toBe('Harina');
    expect(text('stock-warehouse')).toBe('Central');
    expect(text('stock-requested')).toBe('3.000 u');
    expect(text('stock-available')).toBe('2.000 u');
    expect(component.form.controls.countedQuantity.value).toBe('7');
    expect(component.form.controls.reason.value).toBe('Conteo físico');
    component.form.controls.countedQuantity.setValue('6');
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="insufficient-stock"]')).toBeNull();
  });

  it('returns to edit with the server message on a validation error (AC-01)', () => {
    api.confirm.and.returnValue(
      throwError(() => new InventoryApiError('Revisa', 400, { reason: ['El motivo es obligatorio.'] })),
    );
    goToReview('7');
    component.confirm();
    fixture.detectChanges();
    expect(component.step).toBe('edit');
    expect(text('reason-error')).toBe('El motivo es obligatorio.');
    expect(component.saving).toBeFalse();
  });
});

describe('AdjustmentFormComponent coming from the stock detail', () => {
  const P = '11111111-1111-4111-8111-111111111111';
  const W = '22222222-2222-4222-8222-222222222222';
  let fixture: ComponentFixture<AdjustmentFormComponent>;
  let component: AdjustmentFormComponent;
  let api: jasmine.SpyObj<AdjustmentsApiService>;
  let router: Router;

  async function setup(query: Record<string, string>): Promise<void> {
    api = jasmine.createSpyObj<AdjustmentsApiService>('AdjustmentsApiService', ['balance', 'confirm']);
    api.balance.and.returnValue(of(BALANCE));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [makeWarehouse({ id: W })] }));
    const products = jasmine.createSpyObj<OpeningProductsService>('OpeningProductsService', ['search']);
    products.search.and.returnValue(of([{ ...PIECE, id: P }]));
    await TestBed.configureTestingModule({
      imports: [AdjustmentFormComponent],
      providers: [
        provideRouter([]),
        { provide: AdjustmentsApiService, useValue: api },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: OpeningProductsService, useValue: products },
        { provide: ToastrService, useValue: jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']) },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(AdjustmentFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  it('preselects product and warehouse and cancels back to the detail (AC-05, AC-06)', async () => {
    await setup({ return: 'stock', product_id: P, warehouse_id: W });
    expect(component.form.controls.product.value?.id).toBe(P);
    expect(component.form.controls.warehouseId.value).toBe(W);
    const cancel = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('a')).find((a) => a.textContent?.includes('Cancelar'));
    expect(cancel?.getAttribute('href')).toBe(`/pocketbiz/inventory/stock/${P}/${W}`);
  });

  it('returns to the same detail after confirming (AC-06)', async () => {
    await setup({ return: 'stock', product_id: P, warehouse_id: W });
    api.confirm.and.returnValue(of(makeAdjustmentDetail()));
    component.form.controls.countedQuantity.setValue('7');
    component.form.controls.reason.setValue('Conteo físico');
    component.review();
    component.confirm();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/stock', P, W]);
  });
});
