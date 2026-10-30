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
    suppliers = jasmine.createSpyObj<SuppliersApiService>('SuppliersApiService', ['get', 'list']);
    suppliers.get.and.returnValue(of(makeSupplier({ id: 's-1', name: 'Distribuidora Sur' })));
    suppliers.list.and.returnValue(of({ count: 0, next: null, previous: null, results: [] }));
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
  const byTestId = (id: string): HTMLElement => fixture.debugElement.query(By.css(`[data-testid="${id}"]`)).nativeElement as HTMLElement;
  const all = (id: string): HTMLElement[] =>
    fixture.debugElement.queryAll(By.css(`[data-testid="${id}"]`)).map((d) => d.nativeElement as HTMLElement);

  it('lists the purchases with internal reference, date, supplier, total and status (AC-07)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ page: 1, pageSize: 10 }));
    expect(text()).toContain('COM-1A2B3C4D');
    expect(text()).toContain('F-100');
    expect(text()).toContain('29/10/2026');
    expect(text()).toContain('Distribuidora Sur');
    expect(text()).toContain('Bs 25.00');
    expect(text()).toContain('Borrador');
  });

  it('shows reception, payment and balance separately for a confirmed purchase (AC-06, AC-07)', async () => {
    await setup({}, page([
      makePurchaseSummary({
        status: 'confirmed',
        receptionStatus: 'received',
        paymentStatus: 'partial',
        paidTotal: '10.00',
        balance: '15.00',
      }),
    ]));
    expect(byTestId('reception-badge').textContent).toContain('Recibida');
    expect(byTestId('payment-badge').textContent).toContain('Pago parcial');
    expect(byTestId('balance').textContent).toContain('Bs 15.00');
  });

  it('shows a dash where reception, payment and balance do not apply (AC-07)', async () => {
    await setup({}, page([makePurchaseSummary({ status: 'cancelled' })]));
    expect(byTestId('reception-none').textContent).toBe('—');
    expect(byTestId('payment-none').textContent).toBe('—');
    expect(byTestId('balance-none').textContent).toBe('—');
  });

  it('offers a link to start a new purchase and to edit a draft only (AC-07)', async () => {
    await setup({}, page([makePurchaseSummary(), makePurchaseSummary({ id: 'c-2', status: 'confirmed' })]));
    const hrefs = fixture.debugElement.queryAll(By.css('a')).map((a) => (a.nativeElement as HTMLAnchorElement).getAttribute('href'));
    expect(hrefs).toContain('/pocketbiz/purchases/new');
    expect(hrefs).toContain('/pocketbiz/purchases/c-1/edit');
    expect(hrefs).not.toContain('/pocketbiz/purchases/c-2/edit');
  });

  it('shows the empty message when there are no filters (AC-09)', async () => {
    await setup({}, page([]));
    expect(text()).toContain('Aún no hay compras');
    expect(fixture.debugElement.query(By.css('[data-testid="empty-filtered"]'))).toBeNull();
  });

  it('sends the filters of the URL to the API and restores the form (AC-02, AC-08)', async () => {
    await setup({ receptionStatus: 'received', paymentStatus: 'pending', dateFrom: '2026-10-01', q: 'FAC' });
    expect(api.list).toHaveBeenCalledWith({
      supplierId: undefined,
      dateFrom: '2026-10-01',
      dateTo: undefined,
      status: undefined,
      receptionStatus: 'received',
      paymentStatus: 'pending',
      search: 'FAC',
      page: 1,
      pageSize: 10,
    });
    expect(component.filterForm.getRawValue()).toEqual(
      jasmine.objectContaining({ receptionStatus: 'received', paymentStatus: 'pending', dateFrom: '2026-10-01', search: 'FAC' }),
    );
  });

  it('loads the supplier of the URL and sends its id (AC-02, AC-08)', async () => {
    await setup({ supplierId: 's-1' });
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ supplierId: 's-1' }));
    expect(suppliers.get).toHaveBeenCalledWith('s-1');
    expect(component.filterForm.controls.supplier.value?.name).toBe('Distribuidora Sur');
  });

  it('puts the chosen filters in the URL, which triggers the query (AC-08)', async () => {
    await setup();
    component.filterForm.patchValue({ receptionStatus: 'received', paymentStatus: 'pending' }, { emitEvent: false });
    component.applyForm();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases'], {
      queryParams: { receptionStatus: 'received', paymentStatus: 'pending' },
    });
  });

  it('reloads from the first page when the URL changes (AC-08)', async () => {
    await setup();
    component.onPage({ offset: 1 });
    query.next(convertToParamMap({ status: 'confirmed' }));
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'confirmed', page: 1 }));
  });

  it('does not query and flags an inverted date range (AC-11)', async () => {
    await setup();
    component.filterForm.patchValue({ dateFrom: '2026-10-10', dateTo: '2026-10-01' }, { emitEvent: false });
    component.applyForm();
    fixture.detectChanges();
    expect(router.navigate).not.toHaveBeenCalled();
    expect(byTestId('range-error').textContent).toContain('no puede ser anterior');
  });

  it('clears the filters back to the bare list (AC-08)', async () => {
    await setup({ status: 'draft' });
    expect((byTestId('clear-filters') as HTMLButtonElement).disabled).toBeFalse();
    byTestId('clear-filters').click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
  });

  it('with filters and no results shows the applied filters, clear and new purchase (AC-09)', async () => {
    await setup({ receptionStatus: 'received', paymentStatus: 'pending' }, page([]));
    expect(byTestId('empty-filtered').textContent).toContain('No hay compras que coincidan');
    expect(all('applied-filter').map((e) => e.textContent)).toEqual(['Recepción: Recibida', 'Pago: Pago pendiente']);
    expect(byTestId('empty-new').getAttribute('href')).toBe('/pocketbiz/purchases/new');
    byTestId('empty-clear').click();
    expect(router.navigate).toHaveBeenCalledWith(['/pocketbiz/purchases']);
  });

  it('shows the error with a retry button (AC-11)', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new PurchaseApiError('No se pudo conectar con el servidor. Inténtalo de nuevo.', 0)));
    component.retry();
    fixture.detectChanges();
    expect(text()).toContain('No se pudo conectar');
    api.list.and.returnValue(of(page([makePurchaseSummary()])));
    byTestId('retry').click();
    fixture.detectChanges();
    expect(component.errorMessage).toBe('');
    expect(component.rows.length).toBe(1);
  });

  it('requests another page from the server keeping the filters (AC-02)', async () => {
    await setup({ status: 'confirmed' });
    component.onPage({ offset: 1 });
    expect(api.list).toHaveBeenCalledWith(jasmine.objectContaining({ status: 'confirmed', page: 2, pageSize: 10 }));
  });
});
