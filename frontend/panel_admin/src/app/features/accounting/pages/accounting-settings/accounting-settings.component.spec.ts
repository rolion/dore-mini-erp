import { TestBed } from '@angular/core/testing';
import { ActivatedRoute, Router, convertToParamMap, provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiService } from '../../services/accounting-api.service';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { AccountingSettingsComponent } from './accounting-settings.component';

function setup(tab: string | null = null) {
  const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccountClasses']);
  api.listAccountClasses.and.returnValue(of([{ code: 'ASSET', enabled: true }]));
  TestBed.configureTestingModule({
    imports: [AccountingSettingsComponent],
    providers: [...provideTestTranslations(), provideRouter([]), { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap(tab ? { tab } : {}) } } }, { provide: AccountingApiService, useValue: api },
      { provide: FiscalPeriodsApiService, useValue: jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', { list: of([]) }) },
      { provide: NgbModal, useValue: {} }, { provide: ToastrService, useValue: {} }],
  });
  const fixture = TestBed.createComponent(AccountingSettingsComponent);
  fixture.detectChanges();
  return fixture;
}

describe('AccountingSettingsComponent', () => {
  it('has only Classifications and Fiscal periods tabs, classifications first (AC-09)', () => {
    const fixture = setup();
    const tabs = Array.from(fixture.nativeElement.querySelectorAll('[role="tab"]') as NodeListOf<HTMLElement>).map((tab) => tab.id);
    expect(tabs).toEqual(['tab-classes', 'tab-periods']);
    expect(fixture.nativeElement.querySelector('#panel-classes')).not.toBeNull();
    fixture.nativeElement.querySelector('#tab-periods').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('#panel-periods')).not.toBeNull();
  });

  it('links to the other settings that still have no module of their own', () => {
    const link = setup().nativeElement.querySelector('[data-testid="legacy-link"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('/pocketbiz/accounting/settings/legacy');
  });

  it('moves between tabs with the arrow keys', () => {
    const fixture = setup();
    (fixture.nativeElement.querySelector('#tab-classes') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('periods');
    (fixture.nativeElement.querySelector('#tab-periods') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('classes');
  });

  it('links to Regularize historical payments so it stays reachable (REV-01)', () => {
    const link = setup().nativeElement.querySelector('[data-testid="regularization-link"]') as HTMLAnchorElement;
    expect(link.getAttribute('href')).toContain('/pocketbiz/accounting/regularization');
  });

  it('redirects old ?tab= bookmarks to their new screen (REV-03)', () => {
    TestBed.resetTestingModule();
    for (const [tab, path, query] of [['accounts', '/pocketbiz/accounting/accounts', undefined], ['methods', '/pocketbiz/accounting/settings/legacy', { tab: 'methods' }], ['cutoff', '/pocketbiz/accounting/settings/legacy', { tab: 'cutoff' }]] as const) {
      TestBed.resetTestingModule();
      const fixture = setupSpying(tab);
      expect(fixture.navigate).toHaveBeenCalledWith([path], query ? { queryParams: query, replaceUrl: true } : { replaceUrl: true });
    }
    TestBed.resetTestingModule();
    expect(setupSpying('periods').component.tab).toBe('periods');
  });
});

function setupSpying(tab: string) {
  const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccountClasses']);
  api.listAccountClasses.and.returnValue(of([{ code: 'ASSET', enabled: true }]));
  TestBed.configureTestingModule({
    imports: [AccountingSettingsComponent],
    providers: [...provideTestTranslations(), provideRouter([]), { provide: ActivatedRoute, useValue: { snapshot: { queryParamMap: convertToParamMap({ tab }) } } },
      { provide: AccountingApiService, useValue: api },
      { provide: FiscalPeriodsApiService, useValue: jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', { list: of([]) }) },
      { provide: NgbModal, useValue: {} }, { provide: ToastrService, useValue: {} }],
  });
  const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
  const fixture = TestBed.createComponent(AccountingSettingsComponent);
  fixture.detectChanges();
  return { navigate, component: fixture.componentInstance };
}
