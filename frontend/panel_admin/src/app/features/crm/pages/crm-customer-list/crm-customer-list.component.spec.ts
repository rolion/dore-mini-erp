import { provideTestTranslations } from '../../../../core/i18n/testing';
import { BreakpointObserver } from '@angular/cdk/layout';
import { ComponentFixture, TestBed, fakeAsync, tick } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { BehaviorSubject, of, throwError } from 'rxjs';
import { Warehouse, WarehousesApiService } from '../../../inventory';
import { CrmCustomerPage } from '../../models/crm-customer';
import { CrmApiError, CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { makeCrmCustomer, makeCrmPage } from '../../testing/crm-fixtures';
import { CrmCustomerListComponent } from './crm-customer-list.component';

const WAREHOUSES = { count: 1, next: null, previous: null, results: [{ id: 'w-1', name: 'Central', description: '', active: true, isDefault: true } as Warehouse] };

describe('CrmCustomerListComponent', () => {
  let fixture: ComponentFixture<CrmCustomerListComponent>;
  let component: CrmCustomerListComponent;
  let api: jasmine.SpyObj<CrmCustomersApiService>;
  let warehouses: jasmine.SpyObj<WarehousesApiService>;
  let compact$: BehaviorSubject<{ matches: boolean }>;

  const ana = makeCrmCustomer({ id: 'a', name: 'Ana Pérez' });
  const beto = makeCrmCustomer({ id: 'b', name: 'Beto', phone: '', lastPurchaseAt: null, orderCount: 0, outstandingAmount: '0.00' });

  async function setup(page: CrmCustomerPage = makeCrmPage([ana, beto]), compact = false): Promise<void> {
    api = jasmine.createSpyObj<CrmCustomersApiService>('CrmCustomersApiService', ['list']);
    api.list.and.returnValue(of(page));
    warehouses = jasmine.createSpyObj<WarehousesApiService>('WarehousesApiService', ['list']);
    warehouses.list.and.returnValue(of(WAREHOUSES));
    compact$ = new BehaviorSubject<{ matches: boolean }>({ matches: compact });
    await TestBed.configureTestingModule({
      imports: [CrmCustomerListComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: CrmCustomersApiService, useValue: api },
        { provide: WarehousesApiService, useValue: warehouses },
        { provide: BreakpointObserver, useValue: { observe: () => compact$ } },
      ],
    }).compileComponents();
    fixture = TestBed.createComponent(CrmCustomerListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('loads the first page and shows rows with a link to the profile (AC-06)', async () => {
    await setup();
    expect(api.list).toHaveBeenCalledWith({ search: '', warehouseId: '', page: 1, pageSize: 10 });
    expect(component.rows.length).toBe(2);
    const link = fixture.debugElement.query(By.css('[data-testid="customer-link"]'));
    expect(link.nativeElement.getAttribute('href')).toContain('/pocketbiz/customers/a');
    expect(text()).toContain('Ana Pérez');
  });

  it('shows the empty state without filters with a way to Customers (AC-07)', async () => {
    await setup(makeCrmPage([]));
    expect(fixture.debugElement.query(By.css('[data-testid="crm-empty"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="go-customers"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="search-badge"]'))).toBeNull();
  });

  it('lists the page without any segment configuration (AC-08)', async () => {
    await setup();
    expect(component.rows.length).toBe(2);
    expect(text().toLowerCase()).not.toContain('segment');
  });

  it('searches after the debounce and returns to page 1', fakeAsync(() => {
    setup().then(() => undefined);
    tick();
    fixture.detectChanges();
    api.list.calls.reset();
    component.searchControl.setValue('ana');
    tick(300);
    expect(api.list).toHaveBeenCalledWith({ search: 'ana', warehouseId: '', page: 1, pageSize: 10 });
  }));

  it('shows filter badges and clear action when a filtered search is empty (AC-07)', async () => {
    await setup();
    api.list.and.returnValue(of(makeCrmPage([])));
    component.searchControl.setValue('zzz', { emitEvent: false });
    component.warehouseControl.setValue('w-1', { emitEvent: false });
    component.applyFilters();
    fixture.detectChanges();
    expect(api.list).toHaveBeenCalledWith({ search: 'zzz', warehouseId: 'w-1', page: 1, pageSize: 10 });
    expect(fixture.debugElement.query(By.css('[data-testid="search-badge"]'))).not.toBeNull();
    expect(fixture.debugElement.query(By.css('[data-testid="branch-badge"]')).nativeElement.textContent).toContain('Central');
    fixture.debugElement.query(By.css('[data-testid="empty-clear"]')).nativeElement.click();
    expect(component.searchControl.value).toBe('');
    expect(component.warehouseControl.value).toBe('');
  });

  it('loads branches only when the filter is available and hides it otherwise (AC-09)', async () => {
    await setup(makeCrmPage([ana], 1, { warehouse_filter_enabled: false }));
    expect(warehouses.list).not.toHaveBeenCalled();
    expect(fixture.debugElement.query(By.css('#crm-branch'))).toBeNull();
  });

  it('offers the branch filter when enabled', async () => {
    await setup();
    expect(warehouses.list).toHaveBeenCalledWith({ active: true, pageSize: 100 });
    expect(fixture.debugElement.query(By.css('#crm-branch'))).not.toBeNull();
  });

  it('hides sales columns when Sales is disabled (AC-09)', async () => {
    await setup(makeCrmPage([ana], 1, { sales_enabled: false, warehouse_filter_enabled: false }));
    expect(text()).not.toContain('30.00');
  });

  it('requests another page', async () => {
    await setup(makeCrmPage([ana], 25));
    component.onPage({ offset: 1 });
    expect(api.list).toHaveBeenCalledWith({ search: '', warehouseId: '', page: 2, pageSize: 10 });
  });

  it('shows an error with retry', async () => {
    await setup();
    api.list.and.returnValue(throwError(() => new CrmApiError('x', 500)));
    component.retry();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="crm-error"]'))).not.toBeNull();
    api.list.and.returnValue(of(makeCrmPage([ana])));
    fixture.debugElement.query(By.css('[data-testid="retry"]')).nativeElement.click();
    fixture.detectChanges();
    expect(fixture.debugElement.query(By.css('[data-testid="crm-error"]'))).toBeNull();
  });

  it('renders cards with collapsible filters on narrow screens', async () => {
    await setup(makeCrmPage([ana, beto]), true);
    expect(fixture.debugElement.queryAll(By.css('[data-testid="crm-card"]')).length).toBe(2);
    expect(component.filtersCollapsed).toBeTrue();
    const calls = api.list.calls.count();
    component.searchControl.setValue('x');
    expect(api.list.calls.count()).toBe(calls); // en compacto no consulta hasta «Aplicar»
    component.applyFilters();
    expect(api.list.calls.count()).toBe(calls + 1);
  });
});
