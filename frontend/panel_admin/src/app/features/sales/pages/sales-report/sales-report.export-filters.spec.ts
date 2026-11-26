import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ModulesService } from '../../../../core/service/modules.service';
import { SalesReportComponent } from './sales-report.component';

const EMPTY = { count: 1, results: [{ id: 'o', code: 'P', order_date: '2026-08-02', customer: null, total: '1.00', balance: '0.00' }], totals: { orders_count: 1, total: '1.00', balance: '0.00' } };

describe('SalesReportComponent export filters (UI path, real service)', () => {
  it('exports with the dates typed in the inputs', () => {
    TestBed.configureTestingModule({
      imports: [SalesReportComponent],
      providers: [...provideTestTranslations(), provideRouter([]), provideHttpClient(), provideHttpClientTesting(),
        { provide: ModulesService, useValue: { isDisabled: () => true } }],
    });
    const http = TestBed.inject(HttpTestingController);
    const fixture = TestBed.createComponent(SalesReportComponent);
    fixture.detectChanges();
    http.expectOne((r) => r.url.endsWith('/orders/paid-report/')).flush(EMPTY);
    const root = fixture.nativeElement as HTMLElement;
    const set = (id: string, value: string): void => {
      const input = root.querySelector(`#${id}`) as HTMLInputElement;
      input.value = value;
      input.dispatchEvent(new Event('input'));
      input.dispatchEvent(new Event('change'));
    };
    set('report-date-from', '2026-08-01');
    http.expectOne((r) => r.url.endsWith('/orders/paid-report/')).flush(EMPTY);
    set('report-date-to', '2026-08-31');
    const list = http.expectOne((r) => r.url.endsWith('/orders/paid-report/'));
    expect(list.request.params.get('date_to')).toBe('2026-08-31');
    list.flush(EMPTY);
    fixture.detectChanges();
    (root.querySelector('[data-testid="export-xlsx"]') as HTMLButtonElement).click();
    const exp = http.expectOne((r) => r.url.includes('/export/xlsx/'));
    expect(exp.request.params.get('date_from')).toBe('2026-08-01');
    expect(exp.request.params.get('date_to')).toBe('2026-08-31');
    exp.flush(new Blob(['x']));
  });
});
