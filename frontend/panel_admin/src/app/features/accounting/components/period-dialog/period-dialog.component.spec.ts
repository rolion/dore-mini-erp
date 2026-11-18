import { TestBed } from '@angular/core/testing';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { fiscalPeriod } from '../../testing/fiscal-period-fixtures';
import { PeriodDialogComponent } from './period-dialog.component';

describe('PeriodDialogComponent', () => {
  let api: jasmine.SpyObj<FiscalPeriodsApiService>;
  let activeModal: jasmine.SpyObj<NgbActiveModal>;

  function create() {
    api = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['create', 'update']);
    activeModal = jasmine.createSpyObj<NgbActiveModal>('NgbActiveModal', ['close', 'dismiss']);
    TestBed.configureTestingModule({
      imports: [PeriodDialogComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: FiscalPeriodsApiService, useValue: api },
        { provide: NgbActiveModal, useValue: activeModal },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(PeriodDialogComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('does not submit a blank name or missing dates', () => {
    const fixture = create();
    fixture.componentInstance.form.patchValue({ name: '  ' });
    fixture.componentInstance.onSubmit();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('rejects an end date before the start date in the form (AC-02)', () => {
    const fixture = create();
    fixture.componentInstance.form.setValue({ name: 'x', startDate: '2026-02-01', endDate: '2026-01-01' });
    fixture.componentInstance.form.controls.endDate.markAsTouched();
    fixture.detectChanges();
    expect(fixture.componentInstance.form.hasError('endBeforeStart')).toBeTrue();
    expect(fixture.nativeElement.querySelector('[data-testid="end-before-start"]')).not.toBeNull();
    fixture.componentInstance.onSubmit();
    expect(api.create).not.toHaveBeenCalled();
  });

  it('creates a trimmed period and closes with it (AC-01)', () => {
    const fixture = create();
    const saved = fiscalPeriod();
    api.create.and.returnValue(of(saved));
    fixture.componentInstance.form.setValue({ name: '  Año 2026 ', startDate: '2026-01-01', endDate: '2026-12-31' });
    fixture.componentInstance.onSubmit();
    expect(api.create).toHaveBeenCalledWith({ name: 'Año 2026', startDate: '2026-01-01', endDate: '2026-12-31' });
    expect(activeModal.close).toHaveBeenCalledWith(saved);
  });

  it('edits an existing period', () => {
    const fixture = create();
    api.update.and.returnValue(of(fiscalPeriod()));
    fixture.componentInstance.edit(fiscalPeriod());
    fixture.componentInstance.onSubmit();
    expect(api.update).toHaveBeenCalledWith('p1', { name: 'Año 2026', startDate: '2026-01-01', endDate: '2026-12-31' });
  });

  it('shows server field errors and keeps what was typed', () => {
    const fixture = create();
    api.create.and.returnValue(throwError(() => new AccountingApiError('Revisa.', 400, { name: ['Ya existe un período con ese nombre.'] })));
    fixture.componentInstance.form.setValue({ name: 'x', startDate: '2026-01-01', endDate: '2026-02-01' });
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Ya existe un período con ese nombre.');
    expect(fixture.componentInstance.form.controls.name.value).toBe('x');
    expect(activeModal.close).not.toHaveBeenCalled();
  });

  it('shows an overlap 409 inside the dialog (AC-03)', () => {
    const fixture = create();
    api.create.and.returnValue(throwError(() => new AccountingApiError('El rango se superpone con: Q1.', 409, {}, 'period_overlap')));
    fixture.componentInstance.form.setValue({ name: 'x', startDate: '2026-01-01', endDate: '2026-02-01' });
    fixture.componentInstance.onSubmit();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('se superpone con: Q1');
  });
});
