import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ReportingApiService } from '../../services/reporting-api.service';
import { makeChannels, makeCustomers, makeExpenses, makeProducts, makeSales } from '../../testing/report-fixtures';
import { CUSTOMER_RANKING_NOTE, PRODUCT_AMOUNT_NOTE, ReportsComponent, percentOf } from './reports.component';

describe('percentOf', () => {
  it('rounds to one decimal and tolerates a zero total', () => {
    expect(percentOf('1', '3')).toBe(33.3);
    expect(percentOf('150.50', '170.50')).toBe(88.3);
    expect(percentOf('5', '0')).toBe(0);
  });
});

describe('ReportsComponent', () => {
  let fixture: ComponentFixture<ReportsComponent>;
  let component: ReportsComponent;
  let api: jasmine.SpyObj<ReportingApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ReportingApiService>('ReportingApiService', [
      'sales',
      'expenses',
      'salesByChannel',
      'topProducts',
      'topCustomers',
    ]);
    api.sales.and.returnValue(of(makeSales()));
    api.expenses.and.returnValue(of(makeExpenses()));
    api.salesByChannel.and.returnValue(of(makeChannels()));
    api.topProducts.and.returnValue(of(makeProducts()));
    api.topCustomers.and.returnValue(of(makeCustomers()));
    await TestBed.configureTestingModule({
      imports: [ReportsComponent],
      providers: [provideRouter([]), { provide: ReportingApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(ReportsComponent);
    component = fixture.componentInstance;
  });

  const root = () => fixture.nativeElement as HTMLElement;
  const text = () => root().textContent ?? '';
  const byTestId = (id: string) => root().querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
  const render = () => {
    fixture.detectChanges();
    fixture.detectChanges();
  };

  it('loads the five reports for the current month (AC-26)', () => {
    render();
    for (const spy of [api.sales, api.expenses, api.salesByChannel, api.topProducts, api.topCustomers]) {
      expect(spy).toHaveBeenCalledOnceWith({ kind: 'month' });
    }
  });

  it('shows the sales and expense totals with the visible criteria (AC-26)', () => {
    render();
    expect(byTestId('sales-total')?.textContent).toContain('Bs 1200.00');
    expect(byTestId('sales-orders')?.textContent).toContain('4 pedidos');
    expect(byTestId('sales-orders')?.textContent).toContain('Bs 300.00');
    expect(byTestId('sales-criteria')?.textContent?.trim()).toBe('Ventas: criterio.');
    expect(byTestId('expenses-total')?.textContent).toContain('Bs 170.50');
  });

  it('shows sales by channel with Spanish labels and percentages (AC-26)', () => {
    render();
    const table = byTestId('channels-table') as HTMLElement;
    expect(table.textContent).toContain('Venta directa');
    expect(table.textContent).toContain('WhatsApp');
    expect(table.textContent).toContain('25%');
    expect(table.textContent).toContain('75%');
  });

  it('shows expenses by category whose table total matches the header total (AC-26)', () => {
    render();
    expect(byTestId('categories-total')?.textContent).toContain('Bs 170.50');
    expect(byTestId('expenses-total')?.textContent).toContain('Bs 170.50');
    const table = byTestId('categories-table') as HTMLElement;
    expect(table.textContent).toContain('Materia prima');
    expect(table.textContent).toContain('Empaque (inactiva)');
    expect(table.textContent).toContain('88.3%');
    expect(byTestId('expenses-chart')).not.toBeNull();
  });

  it('builds the donut from the categories (AC-26)', () => {
    const report = makeExpenses();
    expect(component.chartSeries(report)).toEqual([150.5, 20]);
    expect(component.chartLabels(report)).toEqual(['Materia prima', 'Empaque (inactiva)']);
    expect(component.chart.type).toBe('donut');
  });

  it('shows top products and top customers with their notes (AC-26)', () => {
    render();
    expect((byTestId('products-table') as HTMLElement).textContent).toContain('Pack cuñapé');
    expect((byTestId('products-table') as HTMLElement).textContent).toContain('Bs 175.00');
    expect(byTestId('products-note')?.textContent?.trim()).toBe(PRODUCT_AMOUNT_NOTE);
    const customers = byTestId('customers-table') as HTMLElement;
    expect(customers.textContent).toContain('Ana Pérez');
    expect(customers.querySelector('a')?.getAttribute('href')).toBe('/customers/k1');
    expect(byTestId('customers-note')?.textContent?.trim()).toBe(CUSTOMER_RANKING_NOTE);
  });

  it('shows an empty state in each card without errors (AC-26)', () => {
    api.sales.and.returnValue(of(makeSales({ total: '0.00', ordersCount: 0, averageTicket: null })));
    api.expenses.and.returnValue(of(makeExpenses({ total: '0.00', categories: [] })));
    api.salesByChannel.and.returnValue(of(makeChannels({ channels: [] })));
    api.topProducts.and.returnValue(of(makeProducts({ products: [] })));
    api.topCustomers.and.returnValue(of(makeCustomers({ customers: [] })));
    render();
    for (const id of ['channels-empty', 'categories-empty', 'products-empty', 'customers-empty']) {
      expect(byTestId(id)?.textContent).toContain('Sin datos para este periodo.');
    }
    expect(byTestId('sales-orders')?.textContent).toContain('—');
    expect(text()).not.toContain('NaN');
  });

  it('reloads all five reports when the period changes (AC-26)', () => {
    render();
    (fixture.debugElement.query(By.css('[data-kind="day"]')).nativeElement as HTMLElement).click();
    fixture.detectChanges();
    for (const spy of [api.sales, api.expenses, api.salesByChannel, api.topProducts, api.topCustomers]) {
      expect(spy).toHaveBeenCalledTimes(2);
      expect(spy.calls.mostRecent().args[0]).toEqual({ kind: 'day' });
    }
  });

  it('retries only the failed report (AC-26)', () => {
    api.topProducts.and.returnValues(throwError(() => new Error('No se pudo cargar.')), of(makeProducts()));
    render();
    expect(text()).toContain('No se pudo cargar.');
    expect(byTestId('customers-table')).not.toBeNull();
    api.sales.calls.reset();
    (root().querySelector('[data-testid="card-error"] button') as HTMLElement).click();
    fixture.detectChanges();
    expect(api.topProducts).toHaveBeenCalledTimes(2);
    expect(api.sales).not.toHaveBeenCalled();
    expect(byTestId('products-table')).not.toBeNull();
  });
});
