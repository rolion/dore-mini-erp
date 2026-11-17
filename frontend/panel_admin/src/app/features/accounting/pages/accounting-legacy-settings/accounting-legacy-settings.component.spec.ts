import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ExpenseConfigApiService } from '../../services/expense-config-api.service';
import { AccountingLegacySettingsComponent } from './accounting-legacy-settings.component';

function setup() {
  const api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods', 'listClassifications', 'getSettings']);
  api.listAccounts.and.returnValue(of([]));
  api.listMethods.and.returnValue(of([]));
  api.listClassifications.and.returnValue(of([]));
  api.getSettings.and.returnValue(of({ cutoffDate: null, enabledAt: null, locked: false, gaps: [] }));
  TestBed.configureTestingModule({
    imports: [AccountingLegacySettingsComponent],
    providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: api },
      { provide: ExpenseConfigApiService, useValue: jasmine.createSpyObj<ExpenseConfigApiService>('ExpenseConfigApiService', { listCategories: of([]), getPaymentClassification: of(null) }) },
      { provide: NgbModal, useValue: {} }, { provide: ToastrService, useValue: {} }],
  });
  const fixture = TestBed.createComponent(AccountingLegacySettingsComponent);
  fixture.detectChanges();
  return fixture;
}

describe('AccountingLegacySettingsComponent', () => {
  it('keeps only the settings that have no screen of their own, methods first (AC-09)', () => {
    const fixture = setup();
    expect(fixture.nativeElement.querySelector('#panel-methods')).not.toBeNull();
    for (const gone of ['accounts', 'accountClasses', 'periods']) {
      expect(fixture.nativeElement.querySelector(`#tab-${gone}`)).toBeNull();
    }
    fixture.nativeElement.querySelector('#tab-cutoff').click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('#panel-cutoff')).not.toBeNull();
  });

  it('moves between tabs with the arrow keys', () => {
    const fixture = setup();
    const press = (id: string, key: string) => {
      (fixture.nativeElement.querySelector(`#tab-${id}`) as HTMLElement).dispatchEvent(new KeyboardEvent('keydown', { key, bubbles: true }));
      fixture.detectChanges();
    };
    press('methods', 'ArrowRight');
    expect(fixture.componentInstance.tab).toBe('classifications');
    press('classifications', 'ArrowRight');
    expect(fixture.componentInstance.tab).toBe('expenses');
    press('expenses', 'ArrowRight');
    expect(fixture.componentInstance.tab).toBe('cutoff');
    press('cutoff', 'ArrowRight');
    expect(fixture.componentInstance.tab).toBe('methods');
  });
});
