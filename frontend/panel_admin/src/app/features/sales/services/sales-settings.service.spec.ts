import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';
import { NO_SALES_DEFAULTS, SalesDefaults, SalesSettingsService } from './sales-settings.service';

describe('SalesSettingsService', () => {
  let service: SalesSettingsService;
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [provideHttpClient(), provideHttpClientTesting()] });
    service = TestBed.inject(SalesSettingsService);
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  const request = (): SalesDefaults[] => {
    const out: SalesDefaults[] = [];
    service.defaults().subscribe((d) => out.push(d));
    return out;
  };
  const flushUrl = () => http.expectOne((r) => r.url.endsWith('/settings/sales/'));

  it('maps the configured default channel and payment method (AC-08)', () => {
    const out = request();
    flushUrl().flush({
      settings: [
        { key: 'sales.default_sales_channel', value: 'FAIR' },
        { key: 'sales.default_payment_method', value: 'QR' },
        { key: 'sales.max_discount_percent', value: '100.00' },
      ],
    });
    expect(out).toEqual([{ salesChannel: 'FAIR', paymentMethod: 'QR' }]);
  });

  it('ignores unknown values and empty defaults (AC-08)', () => {
    const out = request();
    flushUrl().flush({ settings: [{ key: 'sales.default_sales_channel', value: 'TELEGRAM' }] });
    expect(out).toEqual([NO_SALES_DEFAULTS]);
  });

  it('falls back to no defaults when the settings cannot be read (AC-08)', () => {
    const out = request();
    flushUrl().flush({}, { status: 500, statusText: 'Server Error' });
    expect(out).toEqual([NO_SALES_DEFAULTS]);
  });
});
