import { fakeAsync, flushMicrotasks, TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError } from '../../models/accounting';
import { FiscalPeriod } from '../../models/fiscal-period';
import { FiscalPeriodsApiService } from '../../services/fiscal-periods-api.service';
import { fiscalPeriod } from '../../testing/fiscal-period-fixtures';
import { PeriodStatusDialogComponent } from '../period-status-dialog/period-status-dialog.component';
import { PeriodsTabComponent } from './periods-tab.component';

describe('PeriodsTabComponent', () => {
  let api: jasmine.SpyObj<FiscalPeriodsApiService>;
  let modal: jasmine.SpyObj<NgbModal>;
  let dialog: { period?: FiscalPeriod; action?: string; edit?: jasmine.Spy };

  function create(rows: FiscalPeriod[] | 'error') {
    api = jasmine.createSpyObj<FiscalPeriodsApiService>('FiscalPeriodsApiService', ['list', 'close', 'reopen']);
    api.list.and.returnValue(rows === 'error' ? throwError(() => new AccountingApiError('No se pudo cargar.', 500)) : of(rows));
    dialog = { edit: jasmine.createSpy('edit') };
    modal = jasmine.createSpyObj<NgbModal>('NgbModal', ['open']);
    modal.open.and.callFake(() => ({ componentInstance: dialog, result: Promise.resolve(true) }) as never);
    TestBed.configureTestingModule({
      imports: [PeriodsTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: FiscalPeriodsApiService, useValue: api },
        { provide: NgbModal, useValue: modal },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(PeriodsTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows the empty state explaining the consequence (UI-01)', () => {
    expect(create([]).nativeElement.textContent).toContain('Aún no hay períodos fiscales');
  });

  it('shows an error with retry', () => {
    const fixture = create('error');
    expect(fixture.nativeElement.textContent).toContain('No se pudo cargar.');
    fixture.nativeElement.querySelector('button.btn-light').click();
    expect(api.list).toHaveBeenCalledTimes(2);
  });

  it('lists periods with state text and per-state actions (UI-01)', () => {
    const fixture = create([fiscalPeriod(), fiscalPeriod({ id: 'p0', name: 'Año 2025', status: 'CLOSED', isOpen: false, closedByName: 'Ana' })]);
    const text = fixture.nativeElement.textContent as string;
    expect(text).toContain('Abierto');
    expect(text).toContain('Cerrado');
    expect(text).toContain('01/01/2026');
    expect(fixture.nativeElement.querySelectorAll('button[aria-label="Cerrar período"]').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('button[aria-label="Reabrir período"]').length).toBe(1);
    expect(fixture.nativeElement.querySelectorAll('button[aria-label="Editar"]').length).toBe(1);
  });

  it('asks for confirmation and then closes the period (AC-05, UI-02)', fakeAsync(() => {
    const open = fiscalPeriod();
    const fixture = create([open]);
    api.close.and.returnValue(of({ ...open, status: 'CLOSED', isOpen: false }));
    fixture.componentInstance.confirm(open, 'close');
    flushMicrotasks();
    expect(modal.open).toHaveBeenCalledWith(PeriodStatusDialogComponent, jasmine.objectContaining({ centered: true }));
    expect(dialog.period).toBe(open);
    expect(api.close).toHaveBeenCalledWith('p1');
    expect(api.list).toHaveBeenCalledTimes(2);
  }));

  it('does not close when the confirmation is cancelled', fakeAsync(() => {
    const fixture = create([fiscalPeriod()]);
    modal.open.and.callFake(() => ({ componentInstance: dialog, result: Promise.reject('cancel') }) as never);
    fixture.componentInstance.confirm(fiscalPeriod(), 'close');
    flushMicrotasks();
    expect(api.close).not.toHaveBeenCalled();
  }));

  it('reopens a closed period', fakeAsync(() => {
    const closed = fiscalPeriod({ status: 'CLOSED', isOpen: false });
    const fixture = create([closed]);
    api.reopen.and.returnValue(of({ ...closed, status: 'OPEN', isOpen: true }));
    fixture.componentInstance.confirm(closed, 'reopen');
    flushMicrotasks();
    expect(api.reopen).toHaveBeenCalledWith('p1');
  }));

  it('shows the 409 reason on the table (AC-05)', fakeAsync(() => {
    const fixture = create([fiscalPeriod()]);
    api.close.and.returnValue(throwError(() => new AccountingApiError('Ya está cerrado.', 409, {}, 'period_invalid_state')));
    fixture.componentInstance.confirm(fiscalPeriod(), 'close');
    flushMicrotasks();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('.alert-warning').textContent).toContain('Ya está cerrado.');
  }));

  it('opens the dialog preloaded when editing', () => {
    const fixture = create([fiscalPeriod()]);
    fixture.componentInstance.openDialog(fiscalPeriod());
    expect(dialog.edit).toHaveBeenCalled();
  });
});
