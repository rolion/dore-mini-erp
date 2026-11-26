import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ModulesService } from '../../../../core/service/modules.service';
import { fiscalPeriod } from '../../../accounting/testing/fiscal-period-fixtures';
import { FiscalPeriodsApiService } from '../../../accounting/services/fiscal-periods-api.service';
import { PaidReportPage } from '../../models/paid-report';
import { PaidReportApiService } from '../../services/paid-report-api.service';
import { PaidReportComponent } from './paid-report.component';

const PAGE: PaidReportPage = {
  count: 2,
  rows: [
    { id: 'o1', code: 'PED-1', orderDate: '2026-02-01', customerName: 'Ana Pérez', total: '100.00', balance: '0.00' },
    { id: 'o2', code: 'PED-2', orderDate: '2026-02-02', customerName: null, total: '50.00', balance: '0.00' },
  ],
  totals: { ordersCount: 2, total: '150.00', balance: '0.00' },
};
const EMPTY: PaidReportPage = { count: 0, rows: [], totals: { ordersCount: 0, total: '0.00', balance: '0.00' } };

describe('PaidReportComponent', () => {
  let fixture: ComponentFixture<PaidReportComponent>;
  let component: PaidReportComponent;
  let api: jasmine.SpyObj<PaidReportApiService>;
  let periods: jasmine.SpyObj<FiscalPeriodsApiService>;
  let accountingDisabled: boolean;

  const root = (): HTMLElement => fixture.nativeElement as HTMLElement;
  const text = (testId: string): string => root().querySelector(`[data-testid="${testId}"]`)?.textContent ?? '';

  function start(): void {
    fixture = TestBed.createComponent(PaidReportComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  }

  beforeEach(() => {
    accountingDisabled = false;
    api = jasmine.createSpyObj<PaidReportApiService>('PaidReportApiService', ['list', 'export']);
    api.list.and.returnValue(of(PAGE));
    periods = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list']);
    periods.list.and.returnValue(of([fiscalPeriod()]));
    TestBed.configureTestingModule({
      imports: [PaidReportComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: PaidReportApiService, useValue: api },
        { provide: FiscalPeriodsApiService, useValue: periods },
        { provide: ModulesService, useValue: { isDisabled: () => accountingDisabled } },
      ],
    });
  });

  it('loads every paid order up to today on the first page, without filters (AC-04)', () => {
    start();
    expect(api.list).toHaveBeenCalledOnceWith({ dateFrom: '', dateTo: '', fiscalPeriodId: '' }, 1, 10);
    expect(root().querySelectorAll('[data-testid="report-row"]').length).toBe(2);
    expect(text('report-totals')).toContain('150.00');
    expect(text('report-row')).toContain('PED-1');
    expect(root().querySelector('[data-testid="report-row"]:nth-child(2)')?.textContent).toContain('—');
  });

  it('reloads from page 1 with the chosen filters (AC-02, AC-03)', () => {
    start();
    component.filterForm.patchValue({ dateFrom: '2026-01-01', dateTo: '2026-03-31', fiscalPeriodId: 'p1' });
    component.applyFilters();
    expect(api.list).toHaveBeenCalledWith({ dateFrom: '2026-01-01', dateTo: '2026-03-31', fiscalPeriodId: 'p1' }, 1, 10);
  });

  it('refuses an inverted date range without calling the server (AC-02)', () => {
    start();
    api.list.calls.reset();
    component.filterForm.patchValue({ dateFrom: '2026-05-01', dateTo: '2026-01-01' });
    component.applyFilters();
    fixture.detectChanges();
    expect(api.list).not.toHaveBeenCalled();
    expect(root().querySelector('[data-testid="range-error"]')).not.toBeNull();
  });

  it('hides the period selector when Accounting is disabled', () => {
    accountingDisabled = true;
    start();
    expect(periods.list).not.toHaveBeenCalled();
    expect(root().querySelector('#report-period')).toBeNull();
  });

  it('shows the period selector when periods exist', () => {
    start();
    expect(root().querySelector('#report-period')).not.toBeNull();
  });

  it('shows the empty state and disables the exports (UI states)', () => {
    api.list.and.returnValue(of(EMPTY));
    start();
    expect(text('empty')).toContain('Sin registros');
    expect((root().querySelector('[data-testid="export-pdf"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('shows the error with a retry button', () => {
    api.list.and.returnValue(throwError(() => new Error('Falló')));
    start();
    expect(text('error')).toContain('Falló');
    api.list.and.returnValue(of(PAGE));
    (root().querySelector('[data-testid="error"] button') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(root().querySelector('[data-testid="error"]')).toBeNull();
  });

  it('exports each format with the current filters (AC-05)', () => {
    api.export.and.returnValue(of(new Blob(['x'])));
    spyOn(URL, 'createObjectURL').and.returnValue('blob:x');
    spyOn(URL, 'revokeObjectURL');
    spyOn(HTMLAnchorElement.prototype, 'click');
    start();
    component.filterForm.patchValue({ dateFrom: '2026-01-01' });
    (root().querySelector('[data-testid="export-pdf"]') as HTMLButtonElement).click();
    (root().querySelector('[data-testid="export-xlsx"]') as HTMLButtonElement).click();
    expect(api.export).toHaveBeenCalledWith('pdf', { dateFrom: '2026-01-01', dateTo: '', fiscalPeriodId: '' });
    expect(api.export).toHaveBeenCalledWith('xlsx', { dateFrom: '2026-01-01', dateTo: '', fiscalPeriodId: '' });
  });

  it('shows an export failure', () => {
    api.export.and.returnValue(throwError(() => new Error('Demasiados')));
    start();
    component.export('pdf');
    fixture.detectChanges();
    expect(text('export-error')).toContain('Demasiados');
  });
});
