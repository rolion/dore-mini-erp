import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError, Classification } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ClassificationDialogComponent } from './classification-dialog.component';

describe('ClassificationDialogComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  function create() {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['createClassification', 'renameClassification']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [ClassificationDialogComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(ClassificationDialogComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('does not submit a blank name', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ name: '   ' });
    fixture.componentInstance.onSubmit();
    expect(api.createClassification).not.toHaveBeenCalled();
  });

  it('creates a trimmed classification with its direction (AC-06)', () => {
    const fixture = create();
    const saved: Classification = { id: 'c1', name: 'Alquiler', direction: 'EXPENSE', isActive: true };
    api.createClassification.and.returnValue(of(saved));
    fixture.componentInstance.form.patchValue({ name: '  Alquiler ', direction: 'EXPENSE' });
    fixture.componentInstance.onSubmit();
    expect(api.createClassification).toHaveBeenCalledWith({ name: 'Alquiler', direction: 'EXPENSE' });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('only renames when editing and locks the direction (INV-04)', () => {
    const fixture = create();
    const current: Classification = { id: 'c1', name: 'Ventas', direction: 'INCOME', isActive: true };
    fixture.componentInstance.edit(current);
    api.renameClassification.and.returnValue(of({ ...current, name: 'Ventas web' }));
    fixture.componentInstance.form.patchValue({ name: 'Ventas web' });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.form.controls.direction.disabled).toBeTrue();
    expect(api.renameClassification).toHaveBeenCalledWith('c1', 'Ventas web');
  });

  it('shows the server error and keeps the dialog open', () => {
    const fixture = create();
    api.createClassification.and.returnValue(throwError(() => new AccountingApiError('Revisa', 400, { name: ['Ya existe.'] })));
    fixture.componentInstance.form.patchValue({ name: 'Ventas' });
    fixture.componentInstance.onSubmit();
    expect(fixture.componentInstance.serverErrors.name).toBe('Ya existe.');
    expect(activeModal.close).not.toHaveBeenCalled();
  });
});
