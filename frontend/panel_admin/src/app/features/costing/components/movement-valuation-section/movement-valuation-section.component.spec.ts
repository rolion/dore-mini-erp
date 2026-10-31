import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { ModulesService } from '../../../../core/service/modules.service';
import { ValuationApiService } from '../../../inventory/services/valuation-api.service';
import { CostingApiError, MovementValuation } from '../../models/movement-valuation';
import { MovementValuationApiService } from '../../services/movement-valuation-api.service';
import { MovementValuationSectionComponent, NOT_VALUED_MESSAGE } from './movement-valuation-section.component';

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
const ADOPTED = { status: 'adopted' as const, adoption: { id: 'a', cutoffAt: '', method: '', userName: '', lines: [] } };

describe('MovementValuationSectionComponent', () => {
  let fixture: ComponentFixture<MovementValuationSectionComponent>;
  let valuation: jasmine.SpyObj<ValuationApiService>;
  let api: jasmine.SpyObj<MovementValuationApiService>;
  let enabled: BehaviorSubject<ReadonlySet<string> | null>;

  function create(keys: string[] = ['inventory', 'costing']): void {
    enabled.next(new Set(keys));
    fixture = TestBed.createComponent(MovementValuationSectionComponent);
    fixture.componentRef.setInput('sourceType', 'purchase_receipt');
    fixture.componentRef.setInput('sourceId', 'r-1');
    fixture.detectChanges();
  }

  const el = () => fixture.nativeElement as HTMLElement;
  const text = (id: string) => el().querySelector(`[data-testid="${id}"]`)?.textContent?.replace(/\s+/g, ' ').trim() ?? '';

  beforeEach(async () => {
    valuation = jasmine.createSpyObj<ValuationApiService>('ValuationApiService', ['get']);
    valuation.get.and.returnValue(of(ADOPTED));
    api = jasmine.createSpyObj<MovementValuationApiService>('MovementValuationApiService', ['list']);
    api.list.and.returnValue(of({ count: 1, next: null, previous: null, results: [ROW] }));
    enabled = new BehaviorSubject<ReadonlySet<string> | null>(null);
    await TestBed.configureTestingModule({
      imports: [MovementValuationSectionComponent],
      providers: [
        { provide: ValuationApiService, useValue: valuation },
        { provide: MovementValuationApiService, useValue: api },
        { provide: ModulesService, useValue: { enabledKeys$: enabled.asObservable() } },
      ],
    }).compileComponents();
  });

  it('shows the snapshot of the document: cost, value, average and origin (AC-17)', () => {
    create();
    expect(api.list).toHaveBeenCalledWith({ sourceType: 'purchase_receipt', sourceId: 'r-1', movementId: undefined, pageSize: 100 });
    const row = text('valuation-row');
    expect(row).toContain('Harina');
    expect(row).toContain('Bs 8.000000');
    expect(row).toContain('Bs 32.00');
    expect(row).toContain('Bs 5.000000 → Bs 5.857143');
    expect(row).toContain('Precio de compra');
    expect(row).toContain('Valorado');
  });

  it('is hidden without the Costeo module and does not call the API', () => {
    create(['inventory']);
    expect(el().querySelector('[data-testid="valuation-section"]')).toBeNull();
    expect(valuation.get).not.toHaveBeenCalled();
    expect(api.list).not.toHaveBeenCalled();
  });

  it('is hidden while no valuation was adopted', () => {
    valuation.get.and.returnValue(of({ status: 'not_adopted', adoption: null }));
    create();
    expect(el().querySelector('[data-testid="valuation-section"]')).toBeNull();
    expect(api.list).not.toHaveBeenCalled();
  });

  it('explains the empty case: movement before the adoption', () => {
    api.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
    create();
    expect(text('valuation-empty')).toBe(NOT_VALUED_MESSAGE);
  });

  it('shows the error with a retry that reloads', () => {
    api.list.and.returnValues(throwError(() => new CostingApiError('No se pudo cargar.', 500)), of({ count: 1, next: null, previous: null, results: [ROW] }));
    create();
    expect(text('valuation-error')).toContain('No se pudo cargar.');
    (el().querySelector('[data-testid="valuation-retry"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el().querySelector('[data-testid="valuation-row"]')).not.toBeNull();
    expect(el().querySelector('[data-testid="valuation-error"]')).toBeNull();
  });
});
