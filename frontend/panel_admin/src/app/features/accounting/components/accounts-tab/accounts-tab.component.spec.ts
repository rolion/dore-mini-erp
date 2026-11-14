import { TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountsTabComponent } from './accounts-tab.component';

const banco: Account = { id: 'a1', name: 'Banco', currency: 'BOB', isActive: true };

describe('AccountsTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;

  function create(accounts: Account[]) {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'deactivateAccount', 'activateAccount']);
    api.listAccounts.and.returnValue(of(accounts));
    TestBed.configureTestingModule({
      imports: [AccountsTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: NgbModal, useValue: jasmine.createSpyObj('NgbModal', ['open']) },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(AccountsTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows the empty state (UI-04)', () => {
    const fixture = create([]);
    expect(fixture.nativeElement.textContent).toContain('Aún no hay cuentas');
  });

  it('lists accounts filtered by active by default', () => {
    const fixture = create([banco]);
    expect(api.listAccounts).toHaveBeenCalledWith(true);
    expect(fixture.nativeElement.textContent).toContain('Banco');
  });

  it('shows the 409 reason when the account is in use (AC-03)', () => {
    const fixture = create([banco]);
    api.deactivateAccount.and.returnValue(throwError(() => new AccountingApiError('La usan los métodos QR.', 409, {}, 'account_in_use', ['QR'])));
    fixture.componentInstance.toggleActive(banco);
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('La usan los métodos QR.');
  });
});
