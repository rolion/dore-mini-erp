import { TestBed } from '@angular/core/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ACCOUNT_CLASSES, AccountClassState, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountClassesTabComponent } from './account-classes-tab.component';

const all: AccountClassState[] = ACCOUNT_CLASSES.map((code) => ({ code, enabled: true }));

describe('AccountClassesTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  function create(rows: AccountClassState[] = all) {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccountClasses', 'setAccountClassEnabled']);
    api.listAccountClasses.and.returnValue(of(rows));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [AccountClassesTabComponent],
      providers: [...provideTestTranslations(), { provide: AccountingApiService, useValue: api }, { provide: ToastrService, useValue: toastr }],
    });
    const fixture = TestBed.createComponent(AccountClassesTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows exactly the six classifications, including Ingresos (AC-01, AC-07)', () => {
    const fixture = create();
    const text: string = fixture.nativeElement.textContent;
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(6);
    for (const name of ['Activo', 'Pasivo', 'Patrimonio', 'Ingresos', 'Gastos', 'Costos']) {
      expect(text).toContain(name);
    }
  });

  it('has no create, rename or delete controls (AC-04)', () => {
    const fixture = create();
    const labels = Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll('button')).map((b) => b.textContent?.trim());
    expect(labels.every((label) => label === 'Deshabilitar')).toBeTrue();
    expect(fixture.nativeElement.querySelector('input')).toBeNull();
  });

  it('disables a classification and shows its new state (AC-02)', () => {
    const fixture = create();
    api.setAccountClassEnabled.and.returnValue(of({ code: 'COST', enabled: false }));
    fixture.componentInstance.toggle({ code: 'COST', enabled: true });
    fixture.detectChanges();
    expect(api.setAccountClassEnabled).toHaveBeenCalledWith('COST', false);
    expect(fixture.componentInstance.rows.find((r) => r.code === 'COST')?.enabled).toBeFalse();
    expect(fixture.nativeElement.textContent).toContain('Deshabilitada');
    expect(toastr.success).toHaveBeenCalled();
  });

  it('shows a retry when loading fails', () => {
    const fixture = create();
    api.listAccountClasses.and.returnValue(throwError(() => new AccountingApiError('Sin conexión', 0)));
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Sin conexión');
  });

  it('reports a failed toggle without changing the row', () => {
    const fixture = create();
    api.setAccountClassEnabled.and.returnValue(throwError(() => new AccountingApiError('Error', 500)));
    fixture.componentInstance.toggle({ code: 'ASSET', enabled: true });
    expect(toastr.error).toHaveBeenCalledWith('Error');
    expect(fixture.componentInstance.rows.find((r) => r.code === 'ASSET')?.enabled).toBeTrue();
  });
});
