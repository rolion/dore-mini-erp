import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { StockBalance } from '../../models/stock';
import { StockApiService } from '../../services/stock-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { StockListComponent } from './stock-list.component';

const ROW: StockBalance = {
  productId: 'p-1',
  productName: 'Harina',
  warehouseId: 'w-1',
  warehouseName: 'Almacén principal',
  quantity: '10.000',
  unit: { name: 'Unidad', abbreviation: 'u', allowsFractions: false },
};

describe('StockListComponent', () => {
  let stockApi: jasmine.SpyObj<StockApiService>;
  let fixture: ComponentFixture<StockListComponent>;
  let router: Router;

  async function setup(query: Record<string, string> = {}, rows: StockBalance[] = [ROW]): Promise<void> {
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['list']);
    stockApi.list.and.returnValue(of({ count: rows.length, next: null, previous: null, results: rows }));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(
      of({ count: 2, next: null, previous: null, results: [makeWarehouse(), makeWarehouse({ id: 'w-2', name: 'Tienda', isDefault: false })] }),
    );
    await TestBed.configureTestingModule({
      imports: [StockListComponent],
      providers: [
        provideRouter([]),
        { provide: StockApiService, useValue: stockApi },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(StockListComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;

  it('lists balances with quantity and unit and offers «Registrar apertura» (AC-05)', async () => {
    await setup();
    expect(el().querySelector('tbody tr')?.textContent).toContain('Harina');
    expect(el().querySelector('tbody tr')?.textContent).toContain('10 u');
    const link = el().querySelector('[data-testid="register-opening"]') as HTMLAnchorElement;
    expect(link.textContent).toContain('Registrar apertura');
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/stock/opening');
  });

  it('keeps the warehouse sent in the query (after an opening) as the filter (AC-05)', async () => {
    await setup({ warehouse_id: 'w-2' });
    expect(stockApi.list.calls.mostRecent().args[0]?.warehouseId).toBe('w-2');
  });

  it('opens the movements of a row (AC-05)', async () => {
    await setup();
    (el().querySelector('[data-testid="open-movements"]') as HTMLButtonElement).click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/inventory/stock/movements'], {
      queryParams: { warehouse_id: 'w-1', product_id: 'p-1' },
    });
  });

  it('explains the empty state', async () => {
    await setup({}, []);
    expect(el().querySelector('[data-testid="stock-empty"]')?.textContent).toContain('Registrar apertura');
  });

  it('shows the server error with a retry', async () => {
    await setup();
    stockApi.list.and.returnValue(throwError(() => new InventoryApiError('No se pudo conectar con el servidor.', 0)));
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="stock-error"]')?.textContent).toContain('No se pudo conectar');
  });
});
