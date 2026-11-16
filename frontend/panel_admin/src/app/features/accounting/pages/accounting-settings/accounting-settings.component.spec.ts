import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountingSettingsComponent } from './accounting-settings.component';

describe('AccountingSettingsComponent', () => {
  it('shows the accounts tab first and switches to payment methods (UI-01)', () => {
    const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods']);
    const periods = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list']);
    periods.list.and.returnValue(of([]));
    api.listAccounts.and.returnValue(of([]));
    api.listMethods.and.returnValue(of([]));
    TestBed.configureTestingModule({
      imports: [AccountingSettingsComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: api }, { provide: FiscalPeriodsApiService, useValue: periods },
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
    const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods']);
    const periods = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list']);
    periods.list.and.returnValue(of([]));
    api.listAccounts.and.returnValue(of([]));
    api.listMethods.and.returnValue(of([]));
    TestBed.configureTestingModule({
      imports: [AccountingSettingsComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: api }, { provide: FiscalPeriodsApiService, useValue: periods },
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
    expect(fixture.componentInstance.tab).toBe('periods');
    (fixture.nativeElement.querySelector('#tab-periods') as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key: 'ArrowRight', bubbles: true }));
    fixture.detectChanges();
    expect(fixture.componentInstance.tab).toBe('accounts');
  });
});
