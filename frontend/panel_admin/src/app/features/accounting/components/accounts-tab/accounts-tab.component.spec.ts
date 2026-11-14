import { fakeAsync, flushMicrotasks, TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { DeactivateDialogComponent } from '../deactivate-dialog/deactivate-dialog.component';
import { AccountsTabComponent } from './accounts-tab.component';

const banco: Account = { id: 'a1', name: 'Banco', currency: 'BOB', isActive: true };

describe('AccountsTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  let dialog: { account?: Account; methods?: string[] };

  function create(accounts: Account[]) {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'listMethods', 'deactivateAccount', 'activateAccount']);
    api.listMethods.and.returnValue(of([]));
    dialog = {};
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    modal.open.and.callFake(() => ({ componentInstance: dialog, result: Promise.resolve(true) }) as never);
    api.listAccounts.and.returnValue(of(accounts));
    TestBed.configureTestingModule({
      imports: [AccountsTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
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

  it('asks for confirmation before deactivating and then deactivates (REV-03)', fakeAsync(() => {
    const fixture = create([banco]);
    api.deactivateAccount.and.returnValue(of({ ...banco, isActive: false }));
    fixture.componentInstance.toggleActive(banco);
    flushMicrotasks();
    expect(modal.open).toHaveBeenCalledWith(DeactivateDialogComponent, { centered: true });
    expect(dialog.account).toBe(banco);
    expect(dialog.methods).toEqual([]);
    expect(api.deactivateAccount).toHaveBeenCalledWith('a1');
  }));

  it('does not deactivate when the confirmation is cancelled', fakeAsync(() => {
    const fixture = create([banco]);
    modal.open.and.callFake(() => ({ componentInstance: dialog, result: Promise.reject('cancel') }) as never);
    fixture.componentInstance.toggleActive(banco);
    flushMicrotasks();
    expect(api.deactivateAccount).not.toHaveBeenCalled();
  }));

  it('passes the active methods that use the account to the dialog', fakeAsync(() => {
    const fixture = create([banco]);
    api.listMethods.and.returnValue(of([
      { code: 'QR', label: 'QR', isActive: true, account: banco },
      { code: 'CARD', label: 'Tarjeta', isActive: false, account: banco },
      { code: 'CASH', label: 'Efectivo', isActive: true, account: null },
    ]));
    api.deactivateAccount.and.returnValue(of({ ...banco, isActive: false }));
    fixture.componentInstance.toggleActive(banco);
    flushMicrotasks();
    expect(dialog.methods).toEqual(['QR']);
  }));

  it('shows the 409 reason when the server still rejects the deactivation (AC-03)', fakeAsync(() => {
    const fixture = create([banco]);
    api.deactivateAccount.and.returnValue(throwError(() => new AccountingApiError('La usan los métodos QR.', 409, {}, 'account_in_use', ['QR'])));
    fixture.componentInstance.toggleActive(banco);
    flushMicrotasks();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('La usan los métodos QR.');
  }));
});
