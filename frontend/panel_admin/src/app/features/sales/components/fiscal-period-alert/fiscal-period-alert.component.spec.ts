import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ModulesService } from '../../../../core/service/modules.service';
import { FiscalPeriodAlertComponent, FiscalPeriodErrorCode, isFiscalPeriodErrorCode } from './fiscal-period-alert.component';

describe('FiscalPeriodAlertComponent', () => {
  let fixture: ComponentFixture<FiscalPeriodAlertComponent>;
  let enabled: Set<string>;

  function render(code: FiscalPeriodErrorCode): HTMLElement {
    fixture = TestBed.createComponent(FiscalPeriodAlertComponent);
    fixture.componentRef.setInput('code', code);
    fixture.detectChanges();
    return fixture.nativeElement as HTMLElement;
  }

  beforeEach(() => {
    enabled = new Set(['sales']);
    TestBed.configureTestingModule({
      imports: [FiscalPeriodAlertComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: ModulesService, useValue: { get enabledKeysValue() { return enabled; } } },
      ],
    });
  });

  it('explains that the date has no fiscal period (UI-03)', () => {
    const element = render('fiscal_period_missing');
    expect(element.querySelector('[data-testid="fiscal-period-message"]')?.textContent).toContain('ningún período fiscal');
  });

  it('explains that the period is closed (UI-03)', () => {
    const element = render('fiscal_period_closed');
    expect(element.querySelector('[data-testid="fiscal-period-message"]')?.textContent).toContain('está cerrado');
  });

  it('offers the link to the periods only when Accounting is enabled (UI-03)', () => {
    expect(render('fiscal_period_missing').querySelector('[data-testid="fiscal-period-link"]')).toBeNull();
    enabled.add('accounting');
    const element = render('fiscal_period_missing');
    expect(element.querySelector('[data-testid="fiscal-period-link"]')?.getAttribute('href'))
      .toContain('/pocketbiz/accounting/settings');
  });

  it('recognises only the two fiscal period codes', () => {
    expect(isFiscalPeriodErrorCode('fiscal_period_missing')).toBeTrue();
    expect(isFiscalPeriodErrorCode('fiscal_period_closed')).toBeTrue();
    expect(isFiscalPeriodErrorCode('insufficient_stock')).toBeFalse();
  });
});
