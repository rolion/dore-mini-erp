import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { ACCOUNT_CLASSES, Account, AccountClassState, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { AccountDialogComponent } from './account-dialog.component';

let classStates: AccountClassState[] = [];

describe('AccountDialogComponent', () => {
  beforeEach(() => (classStates = ACCOUNT_CLASSES.map((code) => ({ code, enabled: true }))));

  let api: jasmine.SpyObj<AccountingApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  function create() {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['createAccount', 'updateAccount', 'listAccountClasses']);
    api.listAccountClasses.and.returnValue(of(classStates));
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

  const base = { code: '111001', name: 'Caja', currency: 'BOB', accountClass: 'ASSET' as const };
  const saved: Account = { id: 'a1', name: 'Caja', code: '111001', currency: 'BOB', kind: 'CASH', accountClass: 'ASSET', openingBalance: '0.00', isActive: true };

  it('does not submit a blank name or a blank code', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ ...base, name: '   ' });
    fixture.componentInstance.onSubmit();
    fixture.componentInstance.form.patchValue({ name: 'Caja', code: '  ' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).not.toHaveBeenCalled();
    expect(fixture.componentInstance.form.invalid).toBeTrue();
  });

  it('validates the code format and requires a classification (AC-02)', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ ...base, code: '1.1.1.001', accountClass: '' });
    expect(fixture.componentInstance.form.controls.code.invalid).toBeTrue();
    expect(fixture.componentInstance.form.controls.accountClass.invalid).toBeTrue();
    fixture.componentInstance.form.patchValue({ code: 'A111' });
    expect(fixture.componentInstance.form.controls.code.invalid).toBeTrue();
    fixture.componentInstance.form.patchValue({ code: '0111001' });
    expect(fixture.componentInstance.form.controls.code.valid).toBeTrue();
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).not.toHaveBeenCalled();
  });

  it('creates Caja/101/Activo with a trimmed code, without a money type when none is chosen (AC-01)', () => {
    const fixture = create();
    api.createAccount.and.returnValue(of(saved));
    fixture.componentInstance.form.patchValue({ ...base, code: '  101 ', name: '  Caja  ' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).toHaveBeenCalledWith({ code: '101', name: 'Caja', currency: 'BOB', accountClass: 'ASSET', isContra: false, openingBalance: '0.00' });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('offers the money type only for Activo and drops it when the classification changes (AC-05)', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ ...base, kind: 'BANK' });
    expect(fixture.componentInstance.showKind).toBeTrue();
    fixture.componentInstance.form.patchValue({ accountClass: 'EXPENSE' });
    expect(fixture.componentInstance.showKind).toBeFalse();
    expect(fixture.componentInstance.form.controls.kind.value).toBe('');
    api.createAccount.and.returnValue(of(saved));
    fixture.componentInstance.onSubmit();
    expect(api.createAccount.calls.mostRecent().args[0].kind).toBeUndefined();
  });

  it('locks the classification and the contra flag when the account has entries and still submits them unchanged (REV-02)', () => {
    const fixture = create();
    const withEntries: Account = { ...saved, isContra: true, hasEntries: true };
    fixture.componentInstance.edit(withEntries);
    fixture.detectChanges();
    expect(fixture.componentInstance.locked).toBeTrue();
    expect(fixture.componentInstance.form.controls.accountClass.disabled).toBeTrue();
    expect(fixture.componentInstance.form.controls.isContra.disabled).toBeTrue();
    expect(fixture.nativeElement.querySelector('#account-class').disabled).toBeTrue();
    expect(fixture.nativeElement.querySelector('#account-contra').disabled).toBeTrue();
    api.updateAccount.and.returnValue(of({ ...withEntries, name: 'Caja chica' }));
    fixture.componentInstance.form.patchValue({ name: 'Caja chica' });
    fixture.componentInstance.onSubmit();
    const body = api.updateAccount.calls.mostRecent().args[1];
    expect([body.accountClass, body.isContra, body.name]).toEqual(['ASSET', true, 'Caja chica']);
  });

  it('keeps the classification and the contra flag editable when the account has no entries (REV-02)', () => {
    const fixture = create();
    fixture.componentInstance.edit({ ...saved, hasEntries: false });
    expect(fixture.componentInstance.locked).toBeFalse();
    expect(fixture.componentInstance.form.controls.accountClass.enabled).toBeTrue();
    expect(fixture.componentInstance.form.controls.isContra.enabled).toBeTrue();
  });

  it('measures the code length after trimming (REV-05)', () => {
    const fixture = create();
    const twenty = '12345678901234567890';
    fixture.componentInstance.form.patchValue({ code: ` ${twenty} ` });
    expect(fixture.componentInstance.form.controls.code.valid).toBeTrue();
    fixture.componentInstance.form.patchValue({ code: `${twenty}1` });
    expect(fixture.componentInstance.form.controls.code.invalid).toBeTrue();
  });

  it('removes the money type of an existing account when it is reclassified outside Activo (REV-01)', () => {
    const fixture = create();
    fixture.componentInstance.edit(saved);
    api.updateAccount.and.returnValue(of({ ...saved, accountClass: 'EXPENSE', kind: null }));
    fixture.componentInstance.form.patchValue({ accountClass: 'EXPENSE' });
    fixture.componentInstance.onSubmit();
    expect(api.updateAccount.calls.mostRecent().args[1].kind).toBeNull();
  });

  it('removes the money type when "No es cuenta de dinero" is chosen on an Activo account (REV-01)', () => {
    const fixture = create();
    fixture.componentInstance.edit(saved);
    api.updateAccount.and.returnValue(of({ ...saved, kind: null }));
    fixture.componentInstance.form.patchValue({ kind: '' });
    fixture.componentInstance.onSubmit();
    expect(api.updateAccount.calls.mostRecent().args[1].kind).toBeNull();
  });

  it('shows a kind error next to the classification when the money type is hidden (REV-01)', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ ...base, accountClass: 'EXPENSE' });
    api.createAccount.and.returnValue(throwError(() => new AccountingApiError('Revisa', 400, { kind: ['Solo aplica a cuentas de Activo.'] })));
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Solo aplica a cuentas de Activo.');
  });

  it('sends the contra flag and the money type (AC-06)', () => {
    const fixture = create();
    api.createAccount.and.returnValue(of(saved));
    fixture.componentInstance.form.patchValue({ ...base, code: '121005', name: 'Depreciación acumulada', isContra: true, kind: 'CASH' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount).toHaveBeenCalledWith({
      code: '121005',
      name: 'Depreciación acumulada',
      currency: 'BOB',
      accountClass: 'ASSET',
      isContra: true,
      openingBalance: '0.00',
      kind: 'CASH',
    });
  });

  it('rejects a negative or malformed opening balance and sends a valid one', () => {
    const fixture = create();
    api.createAccount.and.returnValue(of({ ...saved, openingBalance: '150.50' }));
    for (const bad of ['-5', '1.234', 'abc', '']) {
      fixture.componentInstance.form.patchValue({ ...base, openingBalance: bad });
      fixture.componentInstance.onSubmit();
      expect(fixture.componentInstance.form.controls.openingBalance.invalid).toBeTrue();
    }
    expect(api.createAccount).not.toHaveBeenCalled();
    fixture.componentInstance.form.patchValue({ openingBalance: '150.50' });
    fixture.componentInstance.onSubmit();
    expect(api.createAccount.calls.mostRecent().args[0].openingBalance).toBe('150.50');
  });

  it('edits an existing account and keeps its code and classification', () => {
    const fixture = create();
    fixture.componentInstance.edit(saved);
    api.updateAccount.and.returnValue(of({ ...saved, name: 'Caja chica' }));
    fixture.componentInstance.form.patchValue({ name: 'Caja chica' });
    fixture.componentInstance.onSubmit();
    expect(api.updateAccount).toHaveBeenCalledWith('a1', {
      code: '111001',
      name: 'Caja chica',
      currency: 'BOB',
      accountClass: 'ASSET',
      isContra: false,
      openingBalance: '0.00',
      kind: 'CASH',
    });
    expect(fixture.componentInstance.isEdit).toBeTrue();
  });

  it('asks a legacy account without code or classification to complete them before saving (AC-08)', () => {
    const fixture = create();
    const legacy: Account = { id: 'a1', name: 'Vieja', currency: 'BOB', kind: null, openingBalance: '0.00', isActive: true };
    fixture.componentInstance.edit(legacy);
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.form.controls.code.invalid).toBeTrue();
    expect(fixture.componentInstance.form.controls.accountClass.invalid).toBeTrue();
    expect(api.updateAccount).not.toHaveBeenCalled();
    api.updateAccount.and.returnValue(of({ ...legacy, code: '111002', accountClass: 'ASSET' }));
    fixture.componentInstance.form.patchValue({ code: '111002', accountClass: 'ASSET' });
    fixture.componentInstance.onSubmit();
    expect(api.updateAccount).toHaveBeenCalledWith('a1', { code: '111002', name: 'Vieja', currency: 'BOB', accountClass: 'ASSET', isContra: false, openingBalance: '0.00' });
  });

  it('shows the server field errors for a repeated code and keeps the dialog open (AC-01)', () => {
    const fixture = create();
    api.createAccount.and.returnValue(throwError(() => new AccountingApiError('Revisa', 400, { code: ['Ya existe una cuenta con ese código.'], name: ['Ya existe una cuenta con ese nombre.'] })));
    fixture.componentInstance.form.patchValue(base);
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.componentInstance.serverErrors.code).toBe('Ya existe una cuenta con ese código.');
    expect(fixture.nativeElement.textContent).toContain('Ya existe una cuenta con ese código.');
    expect(fixture.nativeElement.textContent).toContain('Ya existe una cuenta con ese nombre.');
    expect(activeModal.close).not.toHaveBeenCalled();
  });

  it('shows the 409 reason when the classification change is blocked by entries (AC-04)', () => {
    const fixture = create();
    api.updateAccount.and.returnValue(throwError(() => new AccountingApiError('La cuenta ya tiene asientos.', 409, {}, 'account_has_entries')));
    fixture.componentInstance.edit(saved);
    fixture.componentInstance.form.patchValue({ accountClass: 'LIABILITY' });
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('La cuenta ya tiene asientos.');
  });

  it('offers only enabled classifications (AC-02, AC-12)', () => {
    classStates = [
      { code: 'ASSET', enabled: true },
      { code: 'COST', enabled: false },
    ];
    const fixture = create();
    expect(fixture.componentInstance.classOptions.map((o) => o.code)).toEqual(['ASSET']);
  });

  it('keeps the current disabled classification of an existing account selectable', () => {
    classStates = [
      { code: 'ASSET', enabled: true },
      { code: 'COST', enabled: false },
    ];
    const fixture = create();
    fixture.componentInstance.edit({ id: 'a1', name: 'Costos', code: '511001', currency: 'BOB', kind: null, accountClass: 'COST', openingBalance: '0.00', isActive: true });
    expect(fixture.componentInstance.classOptions).toEqual([
      { code: 'ASSET', disabled: false },
      { code: 'COST', disabled: true },
    ]);
  });
});
