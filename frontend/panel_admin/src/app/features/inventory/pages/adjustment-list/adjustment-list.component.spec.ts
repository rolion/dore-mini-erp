import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { StockAdjustment } from '../../models/adjustment';
import { InventoryApiError } from '../../models/api-error';
import { AdjustmentsApiService } from '../../services/adjustments-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeAdjustment } from '../../testing/adjustment-fixtures';
import { makeWarehouse } from '../../testing/inventory-fixtures';
import { AdjustmentListComponent, INVALID_RANGE_MESSAGE } from './adjustment-list.component';

function page<T>(results: T[]): Page<T> {
  return { count: results.length, next: null, previous: null, results };
}

describe('AdjustmentListComponent', () => {
  let fixture: ComponentFixture<AdjustmentListComponent>;
  let component: AdjustmentListComponent;
  let api: jasmine.SpyObj<AdjustmentsApiService>;

  const entry = makeAdjustment({ id: 'a-2', reference: 'AJ-2', kind: 'in', difference: '2.5000', status: 'reversed' });

  async function setup(rows: StockAdjustment[] = [makeAdjustment(), entry]): Promise<void> {
    api = jasmine.createSpyObj<AdjustmentsApiService>('AdjustmentsApiService', ['list']);
    api.list.and.returnValue(of(page(rows)));
    const products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    products.list.and.returnValue(of(page([])));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of(page([makeWarehouse()])));
    await TestBed.configureTestingModule({
      imports: [AdjustmentListComponent],
      providers: [
        provideRouter([]),
        { provide: AdjustmentsApiService, useValue: api },
        { provide: ProductsApiService, useValue: products },
        { provide: WarehousesApiService, useValue: warehouses },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(AdjustmentListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  const root = () => fixture.nativeElement as HTMLElement;
  const rowTexts = () =>
    Array.from(root().querySelectorAll('[data-testid="adjustment-row"]')).map((row) => row.textContent?.replace(/\s+/g, ' ').trim() ?? '');

  it('lists reference, system, counted, difference with direction, user and status (AC-05)', async () => {
    await setup();
    const [first, second] = rowTexts();
    expect(first).toContain('AJ-1A2B3C4D');
    expect(first).toContain('Arroz');
    expect(first).toContain('10 kg');
    expect(first).toContain('7 kg');
    expect(first).toContain('-3 kg');
    expect(first).toContain('ana');
    expect(first).toContain('Confirmado');
    expect(second).toContain('+2.5 kg');
    expect(second).toContain('Revertido');
    const link = root().querySelector('[data-testid="adjustment-row"] a') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/adjustments/a-1');
  });

  it('offers «Nuevo ajuste» and no edit or delete actions', async () => {
    await setup();
    expect(root().querySelector('[data-testid="new-adjustment"]')?.getAttribute('href')).toBe('/pocketbiz/inventory/adjustments/new');
    expect(root().textContent).not.toMatch(/Editar|Eliminar/);
  });

  it('reloads from the first page with the chosen filters (AC-05)', async () => {
    await setup();
    component.filterForm.patchValue({ dateFrom: '2026-10-01', productId: 'p-1', warehouseId: 'w-1' });
    expect(api.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ dateFrom: '2026-10-01', productId: 'p-1', warehouseId: 'w-1', page: 1 }),
    );
  });

  it('rejects an inverted date range without querying', async () => {
    await setup();
    const calls = api.list.calls.count();
    component.filterForm.patchValue({ dateFrom: '2026-10-31', dateTo: '2026-10-01' });
    fixture.detectChanges();
    expect(component.rangeError).toBe(INVALID_RANGE_MESSAGE);
    expect(api.list.calls.count()).toBe(calls);
  });

  it('shows the empty state, and a different one when filters hide everything', async () => {
    await setup([]);
    expect(root().querySelector('[data-testid="empty"]')?.textContent?.trim()).toBe('Aún no hay ajustes de existencias.');
    component.filterForm.patchValue({ productId: 'p-1' });
    fixture.detectChanges();
    expect(root().querySelector('[data-testid="empty"]')?.textContent?.trim()).toBe('Sin ajustes para esos filtros.');
  });

  it('shows the server error with a retry', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new InventoryApiError('Sin conexión', 0)));
    component.reload();
    fixture.detectChanges();
    expect(root().querySelector('[data-testid="error"]')?.textContent).toContain('Sin conexión');
  });
});
