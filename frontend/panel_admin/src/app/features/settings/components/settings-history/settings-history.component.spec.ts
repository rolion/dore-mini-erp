import { ComponentFixture, TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { SettingHistoryPage, SettingsApiError } from '../../models/setting';
import { SettingsApiService } from '../../services/settings-api.service';
import { SettingsHistoryComponent } from './settings-history.component';

const PAGE: SettingHistoryPage = {
  count: 1,
  settings: [{ key: 'sales.max_discount_percent', label: 'Descuento máximo (% del subtotal)' }],
  results: [
    {
      id: '1',
      changedAt: '2026-10-27T14:30:00',
      changedBy: 'Ana Pérez',
      settingKey: 'sales.max_discount_percent',
      settingLabel: 'Descuento máximo (% del subtotal)',
      oldValue: '100.00 %',
      newValue: '10.00 %',
    },
  ],
};

describe('SettingsHistoryComponent', () => {
  let fixture: ComponentFixture<SettingsHistoryComponent>;
  let component: SettingsHistoryComponent;
  let api: jasmine.SpyObj<SettingsApiService>;
  const el = () => fixture.nativeElement as HTMLElement;

  const setup = () => {
    fixture = TestBed.createComponent(SettingsHistoryComponent);
    component = fixture.componentInstance;
    fixture.componentRef.setInput('scope', 'sales');
    fixture.detectChanges();
  };

  beforeEach(() => {
    api = jasmine.createSpyObj<SettingsApiService>('SettingsApiService', ['history']);
    TestBed.configureTestingModule({ imports: [SettingsHistoryComponent], providers: [{ provide: SettingsApiService, useValue: api }] });
  });

  it('lists date, user, setting, previous and new value (AC-06, UI-04)', () => {
    api.history.and.returnValue(of(PAGE));
    setup();
    const cells = Array.from(el().querySelectorAll('tbody td')).map((c) => c.textContent?.trim());
    expect(cells).toEqual(['27/10/2026 14:30', 'Ana Pérez', 'Descuento máximo (% del subtotal)', '100.00 %', '10.00 %']);
    expect(el().querySelectorAll('#history-setting option').length).toBe(2);
  });

  it('shows the empty state (UI-04)', () => {
    api.history.and.returnValue(of({ count: 0, results: [], settings: [] }));
    setup();
    expect(el().textContent).toContain('Sin cambios registrados.');
    expect(el().querySelector('table')).toBeNull();
  });

  it('applies the date and setting filters from page 1 and clears them (AC-06)', () => {
    api.history.and.returnValue(of(PAGE));
    setup();
    component.page = 3;
    component.filters.setValue({ dateFrom: '2026-10-01', dateTo: '2026-10-31', setting: 'sales.max_discount_percent' });
    component.apply();
    expect(api.history).toHaveBeenCalledWith('sales', {
      dateFrom: '2026-10-01',
      dateTo: '2026-10-31',
      setting: 'sales.max_discount_percent',
      page: 1,
    });
    component.clear();
    expect(api.history.calls.mostRecent().args[1]).toEqual({ dateFrom: '', dateTo: '', setting: '', page: 1 });
  });

  it('shows the error with retry (UI-04)', () => {
    api.history.and.returnValue(throwError(() => new SettingsApiError('Falló.', 500)));
    setup();
    expect(el().textContent).toContain('Falló.');
    api.history.and.returnValue(of(PAGE));
    Array.from(el().querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Reintentar')?.click();
    fixture.detectChanges();
    expect(el().querySelector('table')).not.toBeNull();
  });
});
