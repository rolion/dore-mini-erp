import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiService } from '../../services/accounting-api.service';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { ExpenseConfigApiService } from '../../services/expense-config-api.service';
import { AccountingSettingsComponent } from './accounting-settings.component';

describe('AccountingSettingsComponent', () => {
  it('shows the accounts tab first and switches to payment methods (UI-01)', () => {
    const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods', 'listClassifications', 'listAccountClasses', 'getSettings']);
    api.listAccounts.and.returnValue(of([]));
    api.listMethods.and.returnValue(of([]));
    api.listClassifications.and.returnValue(of([]));
    api.listAccountClasses.and.returnValue(of([{ code: 'ASSET', enabled: true }]));
    api.getSettings.and.returnValue(of({ cutoffDate: null, enabledAt: null, locked: false, gaps: [] }));
    TestBed.configureTestingModule({
      imports: [AccountingSettingsComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: api },
        { provide: FiscalPeriodsApiService, useValue: jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', { list: of([]) }) },
        { provide: NgbModal, useValue: {} }, { provide: ToastrService, useValue: {} }],
    });
    const fixture = TestBed.createComponent(AccountingSettingsComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('#panel-accounts')).not.toBeNull();
    fixture.nativeElement.querySelector('#tab-methods').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('#panel-methods')).not.toBeNull();
  });

  it('moves between tabs with the arrow keys (REV-07)', () => {
    const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods', 'listClassifications', 'listAccountClasses', 'getSettings']);
    api.listAccounts.and.returnValue(of([]));
    api.listMethods.and.returnValue(of([]));
    api.listClassifications.and.returnValue(of([]));
    api.listAccountClasses.and.returnValue(of([{ code: 'ASSET', enabled: true }]));
    api.getSettings.and.returnValue(of({ cutoffDate: null, enabledAt: null, locked: false, gaps: [] }));
    TestBed.configureTestingModule({
      imports: [AccountingSettingsComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: api },
        { provide: ExpenseConfigApiService, useValue: jasmine.createSpyObj<ExpenseConfigApiService>('ExpenseConfigApiService', { listCategories: of([]), getPaymentClassification: of(null) }) },
        { provide: FiscalPeriodsApiService, useValue: jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', { list: of([]) }) },
        { provide: NgbModal, useValue: {} }, { provide: ToastrService, useValue: {} }],
    });
    const fixture = TestBed.createComponent(AccountingSettingsComponent);
    fixture.detectChanges();
    const accounts = fixture.nativeElement.querySelector('#tab-accounts') as HTMLElement;
    accounts.dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('methods');
    expect(fixture.nativeElement.querySelector('#tab-methods').getAttribute('tabindex')).toBe('0');
    expect(fixture.nativeElement.querySelector('#tab-accounts').getAttribute('tabindex')).toBe('-1');
    (fixture.nativeElement.querySelector('#tab-methods') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('classifications');
    (fixture.nativeElement.querySelector('#tab-classifications') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('accountClasses');
    (fixture.nativeElement.querySelector('#tab-accountClasses') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('expenses');
    (fixture.nativeElement.querySelector('#tab-expenses') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('cutoff');
    (fixture.nativeElement.querySelector('#tab-cutoff') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('periods');
    (fixture.nativeElement.querySelector('#tab-periods') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('accounts');
  });
});
