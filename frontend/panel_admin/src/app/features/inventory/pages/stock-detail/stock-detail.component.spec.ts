import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Page } from '../../../../shared/models/page';
import { InventoryApiError } from '../../models/api-error';
import { StockMovement } from '../../models/movement';
import { StockPosition } from '../../models/stock';
import { MovementsApiService } from '../../services/movements-api.service';
import { StockApiService } from '../../services/stock-api.service';
import { makeMovement } from '../../testing/inventory-fixtures';
import { StockDetailComponent } from './stock-detail.component';

const POSITION: StockPosition = {
  productId: 'p-1',
  productName: 'Harina',
  productActive: true,
  warehouseId: 'w-1',
  warehouseName: 'Almacén principal',
  warehouseActive: true,
  quantity: '7.0000',
  balanceState: 'positive',
  unit: { abbreviation: 'kg', allowsFractions: true },
  hasHistory: true,
  canRegisterOpening: false,
};

function page(results: StockMovement[]): Page<StockMovement> {
  return { count: results.length, next: null, previous: null, results };
}

describe('StockDetailComponent', () => {
  let stockApi: jasmine.SpyObj<StockApiService>;
  let movementsApi: jasmine.SpyObj<MovementsApiService>;
  let fixture: ComponentFixture<StockDetailComponent>;
  let router: Router;

  async function setup(position: StockPosition | Error = POSITION, movements: StockMovement[] = [makeMovement()]): Promise<void> {
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['get']);
    stockApi.get.and.returnValue(position instanceof Error ? throwError(() => position) : of(position));
    movementsApi = jasmine.createSpyObj<MovementsApiService>('MovementsApiService', ['list']);
    movementsApi.list.and.returnValue(of(page(movements)));
    await TestBed.configureTestingModule({
      imports: [StockDetailComponent],
      providers: [
        provideRouter([]),
        { provide: StockApiService, useValue: stockApi },
        { provide: MovementsApiService, useValue: movementsApi },
        {
          provide: ActivatedRoute,
          useValue: { snapshot: { paramMap: convertToParamMap({ productId: 'p-1', warehouseId: 'w-1' }) } },
        },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(StockDetailComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;
  const text = (testId: string) => el().querySelector(`[data-testid="${testId}"]`)?.textContent ?? '';

  it('shows name, unit, warehouse and current balance, and loads the history of the pair (AC-04)', async () => {
    await setup();
    expect(el().textContent).toContain('Harina');
    expect(el().textContent).toContain('Almacén principal');
    expect(text('unit')).toContain('kg');
    expect(text('balance')).toContain('7');
    expect(movementsApi.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ productId: 'p-1', warehouseId: 'w-1', page: 1, pageSize: 10 }),
    );
    expect(el().querySelectorAll('[data-testid="movement-row"]').length).toBe(1);
    expect(el().querySelector('[data-testid="movement-row"]')?.textContent).toContain('Pedido de venta');
  });

  it('shows a zero balance and an explanation, not an error, when there are no movements (AC-04)', async () => {
    await setup({ ...POSITION, quantity: '0.0000', balanceState: 'zero', hasHistory: false, canRegisterOpening: true }, []);
    expect(text('balance')).toContain('0');
    expect(text('no-movements')).toContain('Sin movimientos');
    expect(el().querySelector('[data-testid="detail-error"]')).toBeNull();
  });

  it('offers «Ver movimientos» always and «Registrar apertura» only when it applies, never «ajuste» (AC-05)', async () => {
    await setup();
    expect(el().querySelector('[data-testid="view-movements"]')).not.toBeNull();
    expect(el().querySelector('[data-testid="register-opening"]')).toBeNull();
    expect(text('opening-note')).toContain('Ya tiene movimientos');
    expect(el().textContent).not.toContain('Registrar ajuste');
  });

  it('shows «Registrar apertura» for a pair without history (INV-05)', async () => {
    await setup({ ...POSITION, hasHistory: false, canRegisterOpening: true });
    const link = el().querySelector('[data-testid="register-opening"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/stock/opening?warehouse_id=w-1');
  });

  it('explains why the opening is not offered for an inactive product (INV-05)', async () => {
    await setup({ ...POSITION, productActive: false, hasHistory: false, canRegisterOpening: false });
    expect(text('product-state')).toContain('Inactivo');
    expect(text('opening-note')).toContain('inactivo');
  });

  it('opens the movements list filtered by product and warehouse (AC-05)', async () => {
    await setup();
    (el().querySelector('[data-testid="view-movements"]') as HTMLButtonElement).click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/movements'], {
      queryParams: { warehouse_id: 'w-1', product_id: 'p-1' },
    });
  });

  it('marks a negative balance with text besides color (AC-03)', async () => {
    await setup({ ...POSITION, quantity: '-1.0000', balanceState: 'negative' });
    expect(text('negative-badge')).toContain('Negativo');
  });

  it('links each movement to its detail and to the source document only when available (AC-04)', async () => {
    await setup(POSITION, [
      makeMovement(),
      makeMovement({ id: 'm-2', source: { type: 'sales_order', label: 'Pedido de venta', id: '9', line: '', reference: '', available: false } }),
    ]);
    expect(el().querySelectorAll('[data-testid="movement-detail"]').length).toBe(2);
    expect(el().querySelectorAll('[data-testid="source-link"]').length).toBe(1);
  });

  it('shows «no encontrada» for an unknown pair', async () => {
    await setup(new InventoryApiError('Existencia no encontrada.', 404));
    expect(text('not-found')).toContain('no encontrada');
  });

  it('shows a server error with retry', async () => {
    await setup(new InventoryApiError('No se pudo conectar con el servidor.', 0));
    expect(text('detail-error')).toContain('No se pudo conectar');
  });
});
