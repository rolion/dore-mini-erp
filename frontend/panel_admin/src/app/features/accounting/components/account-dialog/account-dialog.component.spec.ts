import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountDialogComponent } from './account-dialog.component';

describe('AccountDialogComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  function create() {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['createAccount', 'updateAccount']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [AccountDialogComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(AccountDialogComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('does not submit a blank name', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ name: '   ' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).not.toHaveBeenCalled();
    expect(fixture.componentInstance.form.invalid).toBeTrue();
  });

  it('creates a trimmed account and closes with it', () => {
    const fixture = create();
    const saved = { id: 'a1', name: 'Caja', currency: 'BOB', isActive: true };
    api.createAccount.and.returnValue(of(saved));
    fixture.componentInstance.form.patchValue({ name: '  Caja  ', currency: 'BOB' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).toHaveBeenCalledWith({ name: 'Caja', currency: 'BOB' });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('edits an existing account', () => {
    const fixture = create();
    const account = { id: 'a1', name: 'Caja', currency: 'BOB', isActive: true };
    fixture.componentInstance.edit(account);
    api.updateAccount.and.returnValue(of({ ...account, name: 'Caja chica' }));
    fixture.componentInstance.form.patchValue({ name: 'Caja chica' });
    fixture.componentInstance.onSubmit();
    expect(api.updateAccount).toHaveBeenCalledWith('a1', { name: 'Caja chica', currency: 'BOB' });
    expect(fixture.componentInstance.isEdit).toBeTrue();
  });

  it('shows the server field error and keeps the dialog open', () => {
    const fixture = create();
    api.createAccount.and.returnValue(throwError(() => new AccountingApiError('Revisa', 400, { name: ['Ya existe una cuenta con ese nombre.'] })));
    fixture.componentInstance.form.patchValue({ name: 'Caja' });
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.componentInstance.serverErrors.name).toBe('Ya existe una cuenta con ese nombre.');
    expect(fixture.nativeElement.textContent).toContain('Ya existe una cuenta con ese nombre.');
    expect(activeModal.close).not.toHaveBeenCalled();
  });

  it('shows the 409 reason when the currency change is blocked', () => {
    const fixture = create();
    api.updateAccount.and.returnValue(throwError(() => new AccountingApiError('La usan los métodos QR.', 409, {}, 'account_in_use', ['QR'])));
    fixture.componentInstance.edit({ id: 'a1', name: 'Banco', currency: 'BOB', isActive: true });
    fixture.componentInstance.form.patchValue({ currency: 'USD' });
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('La usan los métodos QR.');
  });
});
