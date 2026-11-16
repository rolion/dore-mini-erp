import { TestBed } from '@angular/core/testing';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiError, Classification } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ClassificationsTabComponent } from './classifications-tab.component';

const ventas: Classification = { id: 'c1', name: 'Ventas', direction: 'INCOME', isActive: true };

describe('ClassificationsTabComponent', () => {
  let api: jasmine.SpyObj<AccountingApiService>;

  function create(rows: Classification[]) {
    api = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', [
      'listClassifications',
      'activateClassification',
      'deactivateClassification',
    ]);
    api.listClassifications.and.returnValue(of(rows));
    TestBed.configureTestingModule({
      imports: [ClassificationsTabComponent],
      providers: [
        ...provideTestTranslations(),
        { provide: AccountingApiService, useValue: api },
        { provide: NgbModal, useValue: jasmine.createSpyObj('NgbModal', ['open']) },
        { provide: ToastrService, useValue: jasmine.createSpyObj('ToastrService', ['success', 'error']) },
      ],
    });
    const fixture = TestBed.createComponent(ClassificationsTabComponent);
    fixture.detectChanges();
    return fixture;
  }

  it('shows the empty state (UI-03)', () => {
    const fixture = create([]);
    expect(fixture.nativeElement.textContent).toContain('Aún no hay clasificaciones');
  });

  it('lists active classifications of every direction by default (UI-02)', () => {
    const fixture = create([ventas]);
    expect(api.listClassifications).toHaveBeenCalledWith({ active: true, direction: undefined });
    expect(fixture.nativeElement.textContent).toContain('Ventas');
  });

  it('filters by direction', () => {
    const fixture = create([ventas]);
    fixture.componentInstance.directionControl.setValue('EXPENSE');
    expect(api.listClassifications).toHaveBeenCalledWith({ active: true, direction: 'EXPENSE' });
  });

  it('deactivates directly and reloads', () => {
    const fixture = create([ventas]);
    api.deactivateClassification.and.returnValue(of({ ...ventas, isActive: false }));
    fixture.componentInstance.toggleActive(ventas);
    expect(api.deactivateClassification).toHaveBeenCalledWith('c1');
    expect(api.listClassifications).toHaveBeenCalledTimes(2);
  });

  it('shows a retry when loading fails (UI-03)', () => {
    const fixture = create([]);
    api.listClassifications.and.returnValue(throwError(() => new AccountingApiError('Sin conexión', 0)));
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('Sin conexión');
  });
});
