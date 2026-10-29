import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';

import { Page } from '../../../../shared/models/page';
import { PurchaseApiError, PurchaseSummary } from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';
import { makePurchaseSummary } from '../../testing/purchase-fixtures';
import { makeSupplier } from '../../testing/supplier-fixtures';
import { PurchaseListComponent } from './purchase-list.component';

const page = (results: PurchaseSummary[]): Page<PurchaseSummary> => ({ count: results.length, next: null, previous: null, results });

describe('PurchaseListComponent', () => {
  let fixture: ComponentFixture<PurchaseListComponent>;
  let component: PurchaseListComponent;
  let api: jasmine.SpyObj<PurchasesApiService>;
  let suppliers: jasmine.SpyObj<SuppliersApiService>;
  let query: BehaviorSubject<ReturnType<typeof convertToParamMap>>;
  let router: Router;

  async function setup(params: Record<string, string> = {}, result = page([makePurchaseSummary()])): Promise<void> {
    api = jasmine.createSpyObj<PurchasesApiService>('PurchasesApiService', ['list']);
    api.list.and.returnValue(of(result));
    suppliers = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['get']);
    suppliers.get.and.returnValue(of(makeSupplier({ name: 'Distribuidora Sur' })));
    query = new BehaviorSubject(convertToParamMap(params));
    await TestBed.configureTestingModule({
      imports: [PurchaseListComponent],
      providers: [
        provideRouter([]),
        { provide: PurchasesApiService, useValue: api },
        { provide: SuppliersApiService, useValue: suppliers },
        { provide: ActivatedRoute, useValue: { queryParamMap: query.asObservable() } },
      ],
    }).compileComponents();
    router = TestBed.inject(Router);
    spyOn(router, 'navigate').and.resolveTo(true);
    fixture = TestBed.createComponent(PurchaseListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('lists the purchases with date, supplier, reference, total and status (AC-13)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith({ supplierId: undefined, page: 1, pageSize: 10 });
    expect(text()).toContain('29/10/2026');
    expect(text()).toContain('Distribuidora Sur');
    expect(text()).toContain('F-100');
    expect(text()).toContain('Bs 25.00');
    expect(text()).toContain('Borrador');
  });

  it('offers a link to start a new purchase and to edit a draft (AC-13)', async () => {
    await setup();
    const hrefs = fixture.debugElement.queryAll(By.css('a')).map((a) => (a.nativeElement as HTMLAnchorElement).getAttribute('href'));
    expect(hrefs).toContain('/pocketbiz/purchases/new');
    expect(hrefs).toContain('/pocketbiz/purchases/c-1/edit');
  });

  it('shows the empty message (AC-13)', async () => {
    await setup({}, page([]));
    expect(text()).toContain('Aún no hay compras');
  });

  it('filters by supplier from the query string and can remove the filter (AC-13)', async () => {
    await setup({ supplierId: 's-1' }, page([]));
    expect(api.list).toHaveBeenCalledWith({ supplierId: 's-1', page: 1, pageSize: 10 });
    expect(suppliers.get).toHaveBeenCalledWith('s-1');
    expect(text()).toContain('Proveedor: Distribuidora Sur');
    expect(text()).toContain('No hay compras para este proveedor.');
    (fixture.debugElement.query(By.css('[data-testid="clear-filter"]')).nativeElement as HTMLButtonElement).click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
  });

  it('reloads when the filter in the URL changes (AC-13)', async () => {
    await setup();
    query.next(convertToParamMap({ supplierId: 's-2' }));
    expect(api.list).toHaveBeenCalledWith({ supplierId: 's-2', page: 1, pageSize: 10 });
  });

  it('shows the error with a retry button (AC-13)', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new PurchaseApiError('No se pudo conectar con el servidor. Inténtalo de nuevo.', 0)));
    component.retry();
    fixture.detectChanges();
    expect(text()).toContain('No se pudo conectar');
    api.list.and.returnValue(of(page([makePurchaseSummary()])));
    (fixture.debugElement.query(By.css('[data-testid="retry"]')).nativeElement as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(component.errorMessage).toBe('');
    expect(component.rows.length).toBe(1);
  });

  it('requests another page from the server (AC-13)', async () => {
    await setup();
    component.onPage({ offset: 1 });
    expect(api.list).toHaveBeenCalledWith({ supplierId: undefined, page: 2, pageSize: 10 });
  });
});
