import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { ActivatedRoute, convertToParamMap, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Page } from '../../../../shared/models/page';
import { InventoryApiError } from '../../models/api-error';
import { StockLot } from '../../models/lot';
import { LotsApiService, toLot } from '../../services/lots-api.service';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { LOT_DTO } from '../../services/lots-api.service.spec';
import { LotListComponent } from './lot-list.component';

const REFRIGERATING = toLot(LOT_DTO);
const RELEASED = toLot({ ...LOT_DTO, id: 'l-2', code: 'L-20261126-0002', status: 'released', physical_quantity: '60.0000', available_quantity: '60.0000' });

function page(results: StockLot[]): Page<StockLot> {
  return { count: results.length, next: null, previous: null, results };
}

describe('LotListComponent', () => {
  let api: jasmine.SpyObj<LotsApiService>;
  let fixture: ComponentFixture<LotListComponent>;

  async function setup(result: Page<StockLot> | Error = page([REFRIGERATING, RELEASED]), query: Record<string, string> = {}): Promise<void> {
    api = jasmine.createSpyObj<LotsApiService>('LotsApiService', ['list']);
    api.list.and.returnValue(result instanceof Error ? throwError(() => result) : of(result));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    await TestBed.configureTestingModule({
      imports: [LotListComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: LotsApiService, useValue: api },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(query) } } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(LotListComponent);
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;
  const rows = () => Array.from(el().querySelectorAll('[data-testid="lot-row"]'));

  it('shows code, physical and available quantity and status of each lot (AC-05, AC-14)', async () => {
    await setup();
    expect(rows().length).toBe(2);
    const first = rows()[0];
    expect(first.querySelector('[data-testid="code"]')?.textContent).toContain('L-20261126-0001');
    expect(first.querySelector('[data-testid="physical"]')?.textContent).toContain('118');
    expect(first.querySelector('[data-testid="available"]')?.textContent).toContain('0');
    expect(first.querySelector('[data-testid="status"]')?.textContent).toContain('En refrigeración');
    expect(first.querySelector('[data-testid="blocked-note"]')).not.toBeNull();
    const second = rows()[1];
    expect(second.querySelector('[data-testid="available"]')?.textContent).toContain('60');
    expect(second.querySelector('[data-testid="blocked-note"]')).toBeNull();
  });

  it('links each lot to the stock of its product and warehouse', async () => {
    await setup();
    const link = rows()[0].querySelector('[data-testid="stock-link"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toBe('/pocketbiz/inventory/stock/p-1/w-1');
  });

  it('shows the empty state, which differs when a filter is active', async () => {
    await setup(page([]));
    expect(el().querySelector('[data-testid="empty"]')?.textContent).toContain('Aún no hay lotes');
  });

  it('shows the error with a retry that reloads', async () => {
    await setup(new InventoryApiError('Falló', 500));
    expect(el().querySelector('[data-testid="error"]')?.textContent).toContain('Falló');
    api.list.and.returnValue(of(page([REFRIGERATING])));
    (el().querySelector('[data-testid="error"] button') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(rows().length).toBe(1);
  });

  it('filters by the product that arrives in the link', async () => {
    await setup(page([REFRIGERATING]), { product_id: 'p-1' });
    expect(api.list.calls.mostRecent().args[0]?.productId).toBe('p-1');
  });

  it('sends the chosen filters and returns to the first page', fakeAsync(() => {
    api = jasmine.createSpyObj<LotsApiService>('LotsApiService', ['list']);
    api.list.and.returnValue(of(page([REFRIGERATING])));
    const warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    TestBed.configureTestingModule({
      imports: [LotListComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: LotsApiService, useValue: api },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap({}) } } },
      ],
    });
    fixture = TestBed.createComponent(LotListComponent);
    fixture.detectChanges();
    fixture.componentInstance.filterForm.patchValue({ search: ' L-2026 ', status: 'released', withStock: true });
    tick(300);
    expect(api.list.calls.mostRecent().args[0]).toEqual(
      jasmine.objectContaining({ search: 'L-2026', status: 'released', withStock: true, page: 1 }),
    );
  }));
});
