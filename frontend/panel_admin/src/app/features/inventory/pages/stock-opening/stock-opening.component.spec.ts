import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { Subject, of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { OpeningProduct, OpeningResult } from '../../models/stock';
import { OpeningProductsService } from '../../services/opening-products.service';
import { StockApiService } from '../../services/stock-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { HISTORY_MESSAGE, StockOpeningComponent } from './stock-opening.component';

const PIECE: OpeningProduct = { id: 'p-1', name: 'Harina', unit: { abbreviation: 'u', allowsFractions: false } };
const KILO: OpeningProduct = { id: 'p-2', name: 'Azúcar', unit: { abbreviation: 'kg', allowsFractions: true } };

const RESULT: OpeningResult = {
  openingId: 'o-1',
  warehouseId: 'w-1',
  movementDate: '2026-10-27',
  reference: 'Inventario inicial',
  lines: [{ productId: 'p-1', quantity: '10.000', movementId: 'm-1' }],
};

describe('StockOpeningComponent', () => {
  let fixture: ComponentFixture<StockOpeningComponent>;
  let component: StockOpeningComponent;
  let stockApi: jasmine.SpyObj<StockApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;
  let router: Router;

  const main = makeWarehouse();
  const second = makeWarehouse({ id: 'w-2', name: 'Sucursal', isDefault: false });

  beforeEach(async () => {
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['register', 'productsWithHistory']);
    stockApi.productsWithHistory.and.returnValue(of([]));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 2, next: null, previous: null, results: [second, main] }));
    const products = jasmine.createSpyObj<OpeningProductsService>('OpeningProductsService', ['search']);
    products.search.and.returnValue(of([PIECE, KILO]));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    await TestBed.configureTestingModule({
      imports: [StockOpeningComponent],
      providers: [
        provideRouter([]),
        { provide: StockApiService, useValue: stockApi },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: OpeningProductsService, useValue: products },
        { provide: ToastrService, useValue: toastr },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(StockOpeningComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  const el = () => fixture.nativeElement as HTMLElement;
  const rows = () => el().querySelectorAll('[data-testid="opening-line"]');

  function fill(index: number, product: OpeningProduct | null, quantity: string): void {
    const group = component.lines.at(index);
    group.controls.product.setValue(product);
    group.controls.quantity.setValue(quantity);
    group.controls.quantity.markAsDirty();
    component.onProductsChanged();
    fixture.detectChanges();
  }

  function fillHeader(reference = 'Inventario inicial'): void {
    component.form.controls.reference.setValue(reference);
    fixture.detectChanges();
  }

  it('starts with the default warehouse, today, and one empty line (AC-01)', () => {
    expect(component.form.controls.warehouseId.value).toBe('w-1');
    expect(component.form.controls.movementDate.value).toBe(component.today);
    expect(rows().length).toBe(1);
    expect(component.hasUnsavedChanges()).toBeFalse();
    expect((el().querySelector('[data-testid="review"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows the base unit of the chosen product as read-only text (AC-04)', () => {
    fill(0, KILO, '2.5');
    expect(el().querySelector('[data-testid="line-unit"]')?.textContent?.trim()).toBe('kg');
    expect(el().querySelector('[data-testid="line-unit"] input')).toBeNull();
  });

  it('adds and removes lines but keeps at least one (AC-04)', () => {
    (el().querySelector('[data-testid="add-line"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(rows().length).toBe(2);
    (el().querySelectorAll('[data-testid="remove-line"]')[1] as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(rows().length).toBe(1);
    expect((el().querySelector('[data-testid="remove-line"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('accepts zero but rejects negatives, text and fractions on a unit without fractions (AC-01)', () => {
    fillHeader();
    fill(0, PIECE, '0');
    expect(component.canReview).toBeTrue();
    for (const bad of ['', '-1', 'abc', '1.5']) {
      fill(0, PIECE, bad);
      expect(component.canReview).withContext(bad).toBeFalse();
      expect(component.quantityMessage(0)).withContext(bad).not.toBeNull();
    }
    fill(0, KILO, '1.5');
    expect(component.canReview).toBeTrue();
    fill(0, KILO, '1.2345');
    expect(component.canReview).toBeFalse();
  });

  it('does not allow the same product twice: it is disabled in the options and flagged (AC-04)', () => {
    fillHeader();
    fill(0, PIECE, '1');
    (el().querySelector('[data-testid="add-line"]') as HTMLButtonElement).click();
    fill(1, { ...PIECE }, '2');
    expect(component.productOptions.find((option) => option.id === 'p-1')?.disabled).toBeTrue();
    expect(component.isDuplicate(1)).toBeTrue();
    expect(component.productMessage(1)).toContain('otra línea');
    expect(component.canReview).toBeFalse();
  });

  it('flags a line whose product already has movements in the warehouse and blocks the review (AC-03)', () => {
    stockApi.productsWithHistory.and.returnValue(of(['p-1']));
    fillHeader();
    fill(0, PIECE, '4');
    expect(stockApi.productsWithHistory).toHaveBeenCalledWith('w-1', ['p-1']);
    expect(rows()[0].classList).toContain('table-warning');
    expect(el().querySelector('[data-testid="history-alert"]')?.textContent).toContain('Harina');
    expect(component.productMessage(0)).toBe(HISTORY_MESSAGE);
    expect(component.canReview).toBeFalse();
    stockApi.productsWithHistory.and.returnValue(of([]));
    component.form.controls.warehouseId.setValue('w-2');
    fixture.detectChanges();
    expect(component.historyNames).toEqual([]);
    expect(component.canReview).toBeTrue();
  });

  it('shows warehouse, products and quantities before confirming, and cancel creates nothing (AC-04)', () => {
    fillHeader();
    fill(0, KILO, '2.500');
    component.review();
    fixture.detectChanges();
    expect(component.step).toBe('review');
    expect(el().querySelector('[data-testid="summary-warehouse"]')?.textContent).toContain('Almacén principal');
    const [year, month, day] = component.form.controls.movementDate.value.split('-');
    expect(el().querySelector('[data-testid="summary-date"]')?.textContent?.trim()).toBe(`${day}/${month}/${year}`);
    expect(el().querySelector('[data-testid="zero-note"]')).toBeNull();
    expect(el().querySelector('[data-testid="summary-line"]')?.textContent).toContain('Azúcar');
    expect(el().querySelector('[data-testid="summary-line"]')?.textContent).toContain('2.5 kg');
    expect(stockApi.register).not.toHaveBeenCalled();
    (el().querySelector('[data-testid="back-to-edit"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(component.step).toBe('edit');
    expect(stockApi.register).not.toHaveBeenCalled();
  });

  it('warns in the summary that zero-quantity lines register no movement (EDGE-01)', () => {
    fillHeader();
    fill(0, PIECE, '0');
    component.review();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="zero-note"]')?.textContent).toContain('no registran movimiento');
  });

  it('confirms once: a second click while pending sends nothing, then goes to stock (AC-02, AC-05)', () => {
    const pending = new Subject<OpeningResult>();
    stockApi.register.and.returnValue(pending);
    fillHeader();
    fill(0, PIECE, '10');
    component.review();
    fixture.detectChanges();
    const confirm = el().querySelector('[data-testid="confirm"]') as HTMLButtonElement;
    confirm.click();
    component.confirm();
    fixture.detectChanges();
    expect(stockApi.register).toHaveBeenCalledTimes(1);
    expect(confirm.disabled).toBeTrue();
    const input = stockApi.register.calls.mostRecent().args[0];
    expect(input.lines).toEqual([{ productId: 'p-1', quantity: '10' }]);
    expect(input.warehouseId).toBe('w-1');
    pending.next(RESULT);
    expect(toastr.success).toHaveBeenCalledWith('Apertura registrada');
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/stock'], { queryParams: { warehouse_id: 'w-1' } });
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('reuses the same opening key when retrying after an error (AC-02)', () => {
    stockApi.register.and.returnValues(
      throwError(() => new InventoryApiError('No se pudo conectar con el servidor. Inténtalo de nuevo.', 0)),
      of(RESULT),
    );
    fillHeader();
    fill(0, PIECE, '10');
    component.review();
    component.confirm();
    fixture.detectChanges();
    expect(component.step).toBe('edit');
    expect(el().querySelector('[data-testid="opening-conflict"]')?.textContent).toContain('No se pudo conectar');
    component.review();
    component.confirm();
    const [first, second] = stockApi.register.calls.allArgs().map(([input]) => input.openingId);
    expect(first).toBeTruthy();
    expect(second).toBe(first);
  });

  it('marks the lines the server reports as already having movements (AC-03)', () => {
    stockApi.register.and.returnValue(
      throwError(
        () => new InventoryApiError('Algunos productos ya tienen movimientos.', 409, {}, 'stock_history_exists', [], ['p-1']),
      ),
    );
    fillHeader();
    fill(0, PIECE, '10');
    component.review();
    component.confirm();
    fixture.detectChanges();
    expect(component.step).toBe('edit');
    expect(component.hasHistory(0)).toBeTrue();
    expect(rows()[0].classList).toContain('table-warning');
    expect(router.navigate).not.toHaveBeenCalled();
  });

  it('shows server validation errors by field and by line (EDGE-02)', () => {
    stockApi.register.and.returnValue(
      throwError(
        () =>
          new InventoryApiError('Revisa los datos ingresados.', 400, { reference: ['Referencia inválida.'] }, null, [
            { quantity: ['La unidad base de este producto no admite fracciones.'] },
          ]),
      ),
    );
    fillHeader();
    fill(0, PIECE, '10');
    component.review();
    component.confirm();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="reference-error"]')?.textContent).toContain('Referencia inválida.');
    expect(el().querySelector('[data-testid="quantity-error"]')?.textContent).toContain('no admite fracciones');
  });

  it('asks before leaving with changes and not after confirming (AC-04)', () => {
    fillHeader('Algo');
    component.form.markAsDirty();
    expect(component.hasUnsavedChanges()).toBeTrue();
    component.completed = true;
    expect(component.hasUnsavedChanges()).toBeFalse();
  });
});

describe('StockOpeningComponent coming from the stock detail', () => {
  const P = '11111111-1111-4111-8111-111111111111';
  const W = '22222222-2222-4222-8222-222222222222';
  let fixture: ComponentFixture<StockOpeningComponent>;
  let component: StockOpeningComponent;
  let stockApi: jasmine.SpyObj<StockApiService>;
  let router: Router;

  beforeEach(async () => {
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['register', 'productsWithHistory']);
    stockApi.productsWithHistory.and.returnValue(of([]));
    stockApi.register.and.returnValue(of({ ...RESULT, warehouseId: W }));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [makeWarehouse({ id: W })] }));
    const products = jasmine.createSpyObj<OpeningProductsService>('OpeningProductsService', ['search']);
    products.search.and.returnValue(of([{ ...PIECE, id: P }, KILO]));
    await TestBed.configureTestingModule({
      imports: [StockOpeningComponent],
      providers: [
        provideRouter([]),
        { provide: StockApiService, useValue: stockApi },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: OpeningProductsService, useValue: products },
        { provide: ToastrService, useValue: jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']) },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { queryParamMap: convertToParamMap({ return: 'stock', product_id: P, warehouse_id: W }) } },
        },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(StockOpeningComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('preselects product and warehouse without marking the form as changed (AC-05)', () => {
    expect(component.lines.at(0).controls.product.value?.id).toBe(P);
    expect(component.form.controls.warehouseId.value).toBe(W);
    expect(component.hasUnsavedChanges()).toBeFalse();
  });

  it('cancels and returns to the same detail after confirming (AC-06)', () => {
    const cancel = Array.from((fixture.nativeElement as HTMLElement).querySelectorAll('a')).find((a) => a.textContent?.includes('Cancelar'));
    expect(cancel?.getAttribute('href')).toBe(`/pocketbiz/inventory/stock/${P}/${W}`);
    component.lines.at(0).controls.quantity.setValue('4');
    component.form.controls.reference.setValue('Inventario inicial');
    component.review();
    component.confirm();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/stock', P, W]);
  });
});
