import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Page } from '../../../../shared/models/page';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { InventoryApiError } from '../../models/api-error';
import { MovementListParams, StockMovement } from '../../models/movement';
import { MovementsApiService } from '../../services/movements-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { makeMovement, makeWarehouse } from '../../testing/inventory-fixtures';
import { INVALID_RANGE_MESSAGE, MovementListComponent } from './movement-list.component';

function page<T>(results: T[]): Page<T> {
  return { count: results.length, next: null, previous: null, results };
}

describe('MovementListComponent', () => {
  let fixture: ComponentFixture<MovementListComponent>;
  let component: MovementListComponent;
  let api: jasmine.SpyObj<MovementsApiService>;

  const exit = makeMovement();
  const entry = makeMovement({
    id: 'm-2',
    kind: 'in',
    quantityIn: '10.0000',
    quantityOut: null,
    reference: '',
    source: null,
  });

  async function setup(rows: StockMovement[] = [exit, entry]): Promise<void> {
    api = jasmine.createSpyObj<MovementsApiService>('MovementsApiService', ['list']);
    api.list.and.returnValue(of(page(rows)));
    const products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    products.list.and.returnValue(of(page([])));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of(page([makeWarehouse()])));
    await TestBed.configureTestingModule({
      imports: [MovementListComponent],
      providers: [
        provideRouter([]),
        { provide: MovementsApiService, useValue: api },
        { provide: ProductsApiService, useValue: products },
        { provide: WarehousesApiService, useValue: warehouses },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(MovementListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const lastParams = (): MovementListParams => api.list.calls.mostRecent().args[0] as MovementListParams;

  it('loads the first page on init (UI-01)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledTimes(1);
    expect(lastParams()).toEqual(jasmine.objectContaining({ page: 1, pageSize: 10 }));
    expect(component.rows.length).toBe(2);
  });

  it('shows entries and exits in separate columns without edit or delete actions (AC-04, AC-08)', async () => {
    await setup();
    const el: HTMLElement = fixture.nativeElement;
    const headers = Array.from(el.querySelectorAll('.datatable-header-cell-label')).map((h) => h.textContent?.trim());
    expect(headers).toEqual(
      jasmine.arrayContaining([
        'Fecha y hora',
        'Referencia',
        'Producto',
        'Almacén',
        'Tipo',
        'Entrada',
        'Salida',
        'Unidad',
        'Origen',
      ]),
    );
    const rows = el.querySelectorAll('datatable-body-row');
    expect(rows[0].querySelector('[data-col="in"]')?.textContent?.trim()).toBe('—');
    expect(rows[0].querySelector('[data-col="out"]')?.textContent?.trim()).toBe('2.5000');
    expect(rows[1].querySelector('[data-col="in"]')?.textContent?.trim()).toBe('10.0000');
    expect(el.textContent).not.toContain('Editar');
    expect(el.textContent).not.toContain('Eliminar');
  });

  it('offers the source document link only when its module is available and a screen exists (AC-07)', async () => {
    await setup();
    expect(component.sourceLink(exit)).toEqual(['/pocketbiz/sales/orders', '42']);
    const source = exit.source!;
    expect(component.sourceLink(makeMovement({ source: { ...source, available: false } }))).toBeNull();
    expect(component.sourceLink(makeMovement({ source: { ...source, type: 'purchase_receipt' } }))).toBeNull();
    expect(component.sourceLink(entry)).toBeNull();
    expect(fixture.debugElement.queryAll(By.css('[data-action="source"]')).length).toBe(1);
  });

  it('reloads from page 1 with the chosen filters (AC-05)', async () => {
    await setup();
    component.filterForm.patchValue({ dateFrom: '2026-10-01', productId: 'p-1', kind: 'in', sourceType: 'none' });
    expect(lastParams()).toEqual(
      jasmine.objectContaining({ dateFrom: '2026-10-01', productId: 'p-1', kind: 'in', sourceType: 'none', page: 1 }),
    );
    component.clearFilters();
    expect(lastParams().productId).toBeUndefined();
    expect(component.filtersActive).toBeFalse();
  });

  it('does not query with an inverted date range (EDGE-05)', async () => {
    await setup();
    api.list.calls.reset();
    component.filterForm.patchValue({ dateFrom: '2026-10-10', dateTo: '2026-10-01' });
    expect(component.rangeError).toBe(INVALID_RANGE_MESSAGE);
    expect(api.list).not.toHaveBeenCalled();
  });

  it('shows an empty state and a retryable error', async () => {
    await setup([]);
    expect(component.messages.emptyMessage).toContain('Sin movimientos');
    api.list.and.returnValue(throwError(() => new InventoryApiError('Sin conexión', 0)));
    component.reload();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('[data-testid="error"]').textContent).toContain('Sin conexión');
  });
});
