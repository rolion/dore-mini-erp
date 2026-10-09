import { ComponentFixture, TestBed } from '@angular/core/testing';
import { By } from '@angular/platform-browser';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { ReportingApiService } from '../../services/reporting-api.service';
import { makePending, makeSummary } from '../../testing/report-fixtures';
import { DashboardComponent, ESTIMATE_NOTE, PENDING_NOTE } from './dashboard.component';

describe('DashboardComponent', () => {
  let fixture: ComponentFixture<DashboardComponent>;
  let component: DashboardComponent;
  let api: jasmine.SpyObj<ReportingApiService>;

  beforeEach(async () => {
    api = jasmine.createSpyObj<ReportingApiService>('ReportingApiService', ['dashboard', 'pending']);
    api.dashboard.and.returnValue(of(makeSummary()));
    api.pending.and.returnValue(of(makePending()));
    await TestBed.configureTestingModule({
      imports: [DashboardComponent],
      providers: [provideRouter([]), { provide: ReportingApiService, useValue: api }],
    }).compileComponents();
    fixture = TestBed.createComponent(DashboardComponent);
    component = fixture.componentInstance;
  });

  const root = () => fixture.nativeElement as HTMLElement;
  const text = () => root().textContent ?? '';
  const byTestId = (id: string) => root().querySelector(`[data-testid="${id}"]`) as HTMLElement | null;
  const render = () => {
    fixture.detectChanges();
    fixture.detectChanges();
  };

  it('replaces the sample content with real indicators for the current month (AC-25)', () => {
    render();
    expect(api.dashboard).toHaveBeenCalledOnceWith({ kind: 'month' });
    expect(byTestId('sales-total')?.textContent).toContain('Bs 1200.00');
    expect(byTestId('expenses-total')?.textContent).toContain('Bs 450.00');
    expect(byTestId('orders-count')?.textContent?.trim()).toBe('4');
    expect(byTestId('average-ticket')?.textContent).toContain('Bs 300.00');
    expect(byTestId('pending-delivery-count')?.textContent?.trim()).toBe('3');
    expect(byTestId('pending-collection-count')?.textContent?.trim()).toBe('2');
    expect(byTestId('pending-collection-balance')?.textContent).toContain('Bs 85.50 por cobrar');
    expect(text()).not.toContain('New Booking');
    expect(text()).not.toContain('Data 1');
  });

  it('labels the profit "Ganancia estimada", explains it is an estimate and never mentions cost or margin (AC-25, UI-03)', () => {
    render();
    expect(text()).toContain('Ganancia estimada');
    expect(byTestId('estimate-note')?.textContent?.trim()).toBe(ESTIMATE_NOTE);
    expect(byTestId('estimated-profit')?.textContent).toContain('Bs 750.00');
    expect(byTestId('estimated-profit')?.classList).toContain('col-green');
    expect(text().toLowerCase()).not.toContain('margen');
    expect(text().toLowerCase()).not.toContain('utilidad neta');
  });

  it('builds the reproducible formula for the tooltip (AC-25)', () => {
    expect(component.profitFormula(makeSummary())).toBe('Bs 1200.00 − Bs 450.00');
  });

  it('shows a negative profit in red (AC-25)', () => {
    api.dashboard.and.returnValue(of(makeSummary({ estimatedProfit: '-150.50' })));
    render();
    expect(byTestId('estimated-profit')?.classList).toContain('col-red');
    expect(byTestId('estimated-profit')?.textContent).toContain('-150.50');
  });

  it('shows the sales criteria sent by the server (AC-25)', () => {
    render();
    expect(byTestId('criteria')?.textContent?.trim()).toBe('Ventas: criterio de prueba.');
  });

  it('shows a dash for the average ticket when there are no orders (AC-25)', () => {
    api.dashboard.and.returnValue(of(makeSummary({ ordersCount: 0, averageTicket: null, salesTotal: '0.00' })));
    render();
    expect(byTestId('average-ticket')?.textContent).toContain('—');
    expect(text()).not.toContain('NaN');
  });

  it('asks for the new period when the selector changes, without reloading the pending lists (AC-25)', () => {
    render();
    api.pending.calls.reset();
    (fixture.debugElement.query(By.css('[data-kind="week"]')).nativeElement as HTMLElement).click();
    fixture.detectChanges();
    expect(api.dashboard.calls.mostRecent().args[0]).toEqual({ kind: 'week' });
    expect(api.dashboard).toHaveBeenCalledTimes(2);
    expect(api.pending).not.toHaveBeenCalled();
  });

  it('shows the effective period returned by the server (AC-25)', () => {
    render();
    expect(byTestId('effective-period')?.textContent).toContain('Del 01/10/2026 al 31/10/2026');
  });

  it('lists the pending orders with links, the independence note and "Ver todos" (AC-25)', () => {
    render();
    expect(text()).toContain(PENDING_NOTE);
    const delivery = byTestId('delivery-table') as HTMLElement;
    expect(delivery.textContent).toContain('01/10/2026');
    expect(delivery.textContent).toContain('Ana Pérez');
    expect(delivery.textContent).toContain('20/10/2026');
    expect(delivery.textContent).toContain('En preparación');
    expect(delivery.querySelector('a')?.getAttribute('href')).toBe('/sales/orders/o1');
    const collection = byTestId('collection-table') as HTMLElement;
    expect(collection.textContent).toContain('Sin cliente');
    expect(collection.textContent).toContain('Bs 50.00');
    expect(collection.textContent).toContain('Parcial');
    expect(byTestId('delivery-all')?.getAttribute('href')).toBe('/sales/orders?status=PENDING_DELIVERY');
    expect(byTestId('collection-all')?.getAttribute('href')).toBe('/sales/orders?status=NOT_CANCELLED&pay=WITH_BALANCE');
  });

  it('says how many are left out when the list is capped', () => {
    api.pending.and.returnValue(of(makePending({ delivery: { count: 12, rows: makePending().delivery.rows } })));
    render();
    expect(text()).toContain('Mostrando 1 de 12.');
  });

  it('shows empty states for the pending lists', () => {
    api.pending.and.returnValue(of({ delivery: { count: 0, rows: [] }, collection: { count: 0, balanceTotal: '0.00', rows: [] } }));
    render();
    expect(byTestId('delivery-empty')?.textContent).toContain('No hay pedidos pendientes de entrega.');
    expect(byTestId('collection-empty')?.textContent).toContain('No hay pedidos pendientes de cobro.');
  });

  it('keeps the rest of the dashboard when one query fails and retries only that one (AC-25)', () => {
    api.pending.and.returnValues(throwError(() => new Error('No se pudo conectar con el servidor.')), of(makePending()));
    render();
    expect(byTestId('sales-total')).not.toBeNull();
    expect(text()).toContain('No se pudo conectar con el servidor.');
    api.dashboard.calls.reset();
    const retry = fixture.debugElement.queryAll(By.css('[data-testid="card-error"] button'))[0];
    (retry.nativeElement as HTMLElement).click();
    fixture.detectChanges();
    expect(api.pending).toHaveBeenCalledTimes(2);
    expect(api.dashboard).not.toHaveBeenCalled();
    expect(byTestId('delivery-table')).not.toBeNull();
  });

  it('shows an error with retry when the indicators fail without hiding the pending lists (AC-25)', () => {
    api.dashboard.and.returnValues(throwError(() => new Error('No se pudo cargar.')), of(makeSummary()));
    render();
    expect(byTestId('indicators-error')?.textContent).toContain('No se pudo cargar.');
    expect(byTestId('delivery-table')).not.toBeNull();
    (byTestId('indicators-error')?.querySelector('button') as HTMLElement).click();
    fixture.detectChanges();
    expect(byTestId('sales-total')).not.toBeNull();
  });

  it('refreshes everything with the update button', () => {
    render();
    (byTestId('refresh') as HTMLElement).click();
    fixture.detectChanges();
    expect(api.dashboard).toHaveBeenCalledTimes(2);
    expect(api.pending).toHaveBeenCalledTimes(2);
  });
});
