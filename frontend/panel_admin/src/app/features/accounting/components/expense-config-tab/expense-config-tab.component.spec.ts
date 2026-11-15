import { TestBed } from '@angular/core/testing';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Classification } from '../../models/accounting';
import { ExpenseConfigError } from '../../models/expense-config';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ExpenseConfigApiService } from '../../services/expense-config-api.service';
import { ExpenseConfigTabComponent } from './expense-config-tab.component';

const rent: Classification = { id: 'c1', name: 'Alquiler', direction: 'EXPENSE', isActive: true };

describe('ExpenseConfigTabComponent', () => {
  let config: jasmine.SpyObj<ExpenseConfigApiService>;
  let toastr: jasmine.SpyObj<ToastrService>;

  function create() {
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listClassifications']);
    accounting.listClassifications.and.returnValue(of([rent]));
    config = jasmine.createSpyObj<ExpenseConfigApiService>('ExpenseConfigApiService', [
      'listCategories',
      'setCategoryClassification',
      'getPaymentClassification',
      'setPaymentClassification',
    ]);
    config.listCategories.and.returnValue(
      of([
        { id: 'k1', name: 'Alquiler', classification: null },
        { id: 'k2', name: 'Luz', classification: { id: 'c9', name: 'Servicios', active: false } },
      ]),
    );
    config.getPaymentClassification.and.returnValue(of(null));
    toastr = jasmine.createSpyObj<ToastrService>('ToastrService', ['success', 'error']);
    TestBed.configureTestingModule({
      imports: [ExpenseConfigTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: accounting },
        { provide: ExpenseConfigApiService, useValue: config },
        { provide: ToastrService, useValue: toastr },
      ],
    });
    const fixture = TestBed.createComponent(ExpenseConfigTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('lists supplier payments first and each category with its status (AC-08)', () => {
    const fixture = create();
    const rows = fixture.componentInstance.rows;
    expect(rows.map((r) => r.label)).toContain('Alquiler');
    expect(rows[0].id).toBeNull();
    expect(fixture.componentInstance.status(rows[1])).toBe('pending');
    expect(fixture.componentInstance.status(rows[2])).toBe('inactive');
    expect(fixture.nativeElement.querySelectorAll('tbody tr').length).toBe(3);
  });

  it('saves a category classification on change (AC-08)', () => {
    const fixture = create();
    config.setCategoryClassification.and.returnValue(of({ id: 'c1', name: 'Alquiler', active: true }));
    const row = fixture.componentInstance.rows[1];
    fixture.componentInstance.onChange(row, 'c1');
    expect(config.setCategoryClassification).toHaveBeenCalledWith('k1', 'c1');
    expect(row.classification?.id).toBe('c1');
    expect(toastr.success).toHaveBeenCalled();
  });

  it('saves the supplier-payments classification and clears it with an empty value (AC-08)', () => {
    const fixture = create();
    config.setPaymentClassification.and.returnValue(of(null));
    fixture.componentInstance.onChange(fixture.componentInstance.rows[0], '');
    expect(config.setPaymentClassification).toHaveBeenCalledWith(null);
  });

  it('shows the API error on the row (AC-08)', () => {
    const fixture = create();
    config.setCategoryClassification.and.returnValue(throwError(() => new ExpenseConfigError('La clasificación está inactiva.', 400)));
    const row = fixture.componentInstance.rows[1];
    fixture.componentInstance.onChange(row, 'c1');
    expect(row.error).toBe('La clasificación está inactiva.');
    expect(row.classification).toBeNull();
  });

  it('keeps the tab usable when Expenses is not enabled', () => {
    const fixture = create();
    config.listCategories.and.returnValue(throwError(() => new ExpenseConfigError('Módulo no habilitado', 403)));
    fixture.componentInstance.reload();
    expect(fixture.componentInstance.warnings).toEqual(['Módulo no habilitado']);
    expect(fixture.componentInstance.rows.length).toBe(1);
  });
});
