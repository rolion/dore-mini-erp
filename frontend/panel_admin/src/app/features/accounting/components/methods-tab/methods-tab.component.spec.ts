import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError, PaymentMethod } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { MethodsTabComponent } from './methods-tab.component';

const caja: Account = { id: 'a1', name: 'Caja', currency: 'BOB', isActive: true };
const dolares: Account = { id: 'a2', name: 'Dólares', currency: 'USD', isActive: true };
const methods = (): PaymentMethod[] => [
  { code: 'CASH', label: 'Efectivo', isActive: true, account: null },
  { code: 'QR', label: 'QR', isActive: true, account: caja },
];

describe('MethodsTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;

  function create(accounts: Account[] = [caja, dolares]): ComponentFixture<MethodsTabComponent> {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listMethods', 'listAccounts', 'configureMethod']);
    api.listMethods.and.returnValue(of(methods()));
    api.listAccounts.and.returnValue(of(accounts));
    TestBed.configureTestingModule({
      imports: [MethodsTabComponent],
      providers: [...provideTestTranslations(), { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) }, { provide: AccountingApiService, useValue: api }],
    });
    const fixture = TestBed.createComponent(MethodsTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('lists the methods and shows non-BOB accounts disabled (UI-03)', () => {
    const fixture = create();
    const rows = fixture.nativeElement.querySelectorAll('tbody tr');
    expect(rows.length).toBe(2);
    const cash = fixture.componentInstance.rows[0];
    expect(fixture.componentInstance.options(cash).map((a) => a.id)).toEqual(['a1', 'a2']);
    expect(fixture.componentInstance.isSelectable(cash, caja)).toBeTrue();
    expect(fixture.componentInstance.isSelectable(cash, dolares)).toBeFalse();
    const options = Array.from<HTMLOptionElement>(rows[0].querySelectorAll('option'));
    const usd = options.find((o) => o.textContent?.includes('Dólares'));
    expect(usd?.disabled).toBeTrue();
    expect(usd?.textContent).toContain('moneda no compatible');
    expect(options.find((o) => o.textContent?.includes('Caja'))?.disabled).toBeFalse();
  });

  it('shows the empty state when there are no accounts (AC-07)', () => {
    const fixture = create([]);
    expect(fixture.nativeElement.querySelector('[data-testid="no-accounts"]')).not.toBeNull();
  });

  it('saves a row with the chosen account and shows the server error otherwise', () => {
    const fixture = create();
    const row = fixture.componentInstance.rows[0];
    row.form.controls.accountId.setValue('a1');
    row.form.markAsDirty();
    api.configureMethod.and.returnValue(of({ ...row.method, account: caja }));
    fixture.componentInstance.save(row);
    expect(api.configureMethod).toHaveBeenCalledWith('CASH', 'a1', true);
    expect(row.method.account?.id).toBe('a1');

    api.configureMethod.and.returnValue(throwError(() => new AccountingApiError('Revisa los datos', 400, { accountId: ['La cuenta está inactiva.'] })));
    row.form.controls.accountId.setValue('a1');
    fixture.componentInstance.save(row);
    expect(row.error).toBe('La cuenta está inactiva.');
  });

  it('shows an error with retry when loading fails', () => {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listMethods', 'listAccounts', 'configureMethod']);
    api.listMethods.and.returnValue(throwError(() => new AccountingApiError('Sin conexión', 0)));
    api.listAccounts.and.returnValue(of([]));
    TestBed.configureTestingModule({
      imports: [MethodsTabComponent],
      providers: [...provideTestTranslations(), { provide: ToastrService, useValue: {} }, { provide: AccountingApiService, useValue: api }],
    });
    const fixture = TestBed.createComponent(MethodsTabComponent);
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Sin conexión');
  });
});
