import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { Product } from '../../../products/models/product';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { CostingApiError, MovementValuation } from '../../models/movement-valuation';
import { MovementValuationApiService } from '../../services/movement-valuation-api.service';
import { INVALID_RANGE_MESSAGE, ValuationMovementsComponent } from './valuation-movements.component';

const ROW: MovementValuation = {
  id: 1,
  movementId: 'm-1',
  productId: 'p-1',
  productName: 'Harina',
  unitAbbreviation: 'kg',
  kind: 'in',
  quantity: '4.0000',
  unitCost: '8.000000',
  value: '32.00',
  averageBefore: '5.000000',
  averageAfter: '5.857143',
  costOrigin: 'purchase_price',
  sourceType: 'purchase_receipt',
  sourceId: 'r-1',
  sourceLabel: 'Recepción de compra',
  occurredAt: '2026-10-30T15:00:00Z',
};

describe('ValuationMovementsComponent', () => {
  let fixture: ComponentFixture<ValuationMovementsComponent>;
  let component: ValuationMovementsComponent;
  let api: jasmine.SpyObj<MovementValuationApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<MovementValuationApiService>('MovementValuationApiService', ['list']);
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [ROW] }));
    const products = jasmine.createSpyObj<ProductsApiService>('ProductsApiService', ['list']);
    products.list.and.returnValue(
      of({ count: 1, next: null, previous: null, results: [{ id: 'p-1', name: 'Harina' } as Product] }),
    );
    await TestBed.configureTestingModule({
      imports: [ValuationMovementsComponent],
      providers: [
        provideRouter([]),
        { provide: MovementValuationApiService, useValue: api },
        { provide: ProductsApiService, useValue: products },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(ValuationMovementsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('loads the first page without filters (AC-18)', () => {
    expect(api.list).toHaveBeenCalledWith({
      dateFrom: undefined,
      dateTo: undefined,
      productId: undefined,
      sourceType: undefined,
      page: 1,
      pageSize: 10,
    });
    expect(component.rows).toEqual([ROW]);
    expect(component.total).toBe(1);
    expect(component.products.length).toBe(1);
  });

  it('reloads from the first page when a filter changes (AC-18)', () => {
    component.filterForm.patchValue({ productId: 'p-1', sourceType: 'purchase_receipt' });
    expect(api.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ productId: 'p-1', sourceType: 'purchase_receipt', page: 1 }),
    );
    expect(component.filtersActive).toBeTrue();
    component.clearFilters();
    expect(component.filtersActive).toBeFalse();
  });

  it('does not query with an inverted date range', () => {
    api.list.calls.reset();
    component.filterForm.patchValue({ dateFrom: '2026-10-31', dateTo: '2026-10-01' });
    expect(component.rangeError).toBe(INVALID_RANGE_MESSAGE);
    expect(api.list).not.toHaveBeenCalled();
  });

  it('asks for the next page only when the page really changes', () => {
    api.list.calls.reset();
    component.onPage({ offset: 0 });
    expect(api.list).not.toHaveBeenCalled();
    component.onPage({ offset: 1 });
    expect(api.list.calls.mostRecent().args[0]?.page).toBe(2);
  });

  it('shows the error with a retry', () => {
    api.list.and.returnValue(throwError(() => new CostingApiError('No se pudo cargar.', 500)));
    component.reload();
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('[data-testid="error"]')?.textContent).toContain(
      'No se pudo cargar.',
    );
  });
});
