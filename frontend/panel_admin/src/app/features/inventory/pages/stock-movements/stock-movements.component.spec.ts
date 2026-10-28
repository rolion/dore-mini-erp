import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { MovementsPage } from '../../models/stock';
import { StockApiService } from '../../services/stock-api.service';
import { StockMovementsComponent } from './stock-movements.component';

const PAGE: MovementsPage = {
  count: 1,
  results: [{ id: 'm-1', movementType: 'opening', quantity: '10.000', movementDate: '2026-10-27', reference: 'Inventario inicial', createdAt: '2026-10-27T10:00:00Z' }],
  summary: {
    productId: 'p-1',
    productName: 'Harina',
    warehouseId: 'w-1',
    warehouseName: 'Almacén principal',
    quantity: '10.000',
    unit: { name: 'Unidad', abbreviation: 'u', allowsFractions: false },
  },
};

describe('StockMovementsComponent', () => {
  let stockApi: jasmine.SpyObj<StockApiService>;
  let fixture: ComponentFixture<StockMovementsComponent>;

  async function setup(query: Record<string, string>): Promise<void> {
    stockApi = jasmine.createSpyObj<StockApiService>('StockApiService', ['movements']);
    stockApi.movements.and.returnValue(of(PAGE));
    await TestBed.configureTestingModule({
      imports: [StockMovementsComponent],
      providers: [
        provideRouter([]),
        { provide: StockApiService, useValue: stockApi },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(StockMovementsComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;

  it('shows the product, the current stock and its opening movement (AC-05)', async () => {
    await setup({ warehouse_id: 'w-1', product_id: 'p-1' });
    expect(stockApi.movements).toHaveBeenCalledWith('w-1', 'p-1', 1, 20);
    expect(el().querySelector('h4')?.textContent).toContain('Harina');
    expect(el().querySelector('[data-testid="movements-summary"]')?.textContent).toContain('10 u');
    const row = el().querySelector('tbody tr')?.textContent ?? '';
    expect(row).toContain('Apertura');
    expect(row).toContain('27/10/2026');
    expect(row).toContain('Inventario inicial');
  });

  it('explains when the product or warehouse is missing from the URL', async () => {
    await setup({});
    expect(stockApi.movements).not.toHaveBeenCalled();
    expect(el().querySelector('[data-testid="movements-error"]')?.textContent).toContain('Falta el producto');
  });

  it('shows the server error', async () => {
    await setup({ warehouse_id: 'w-1', product_id: 'p-1' });
    stockApi.movements.and.returnValue(throwError(() => new InventoryApiError('No hay existencias para ese producto.', 404)));
    fixture.componentInstance.load();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="movements-error"]')?.textContent).toContain('No hay existencias');
  });
});
