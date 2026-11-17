import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { AccountingApiService } from '../../../accounting/services/accounting-api.service';
import { PostingConfigApiService } from '../../../accounting/services/posting-config-api.service';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ALL_ACCOUNTS, expensesConfig } from '../../../accounting/testing/posting-fixtures';
import { ExpenseSettingsComponent } from './expense-settings.component';

describe('ExpenseSettingsComponent', () => {
  it('shows the account configuration of the Expenses module (AC-13)', () => {
    const get = jasmine.createSpy('get').and.returnValue(of(expensesConfig()));
    TestBed.configureTestingModule({
      imports: [ExpenseSettingsComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: PostingConfigApiService, useValue: { get } },
        {
          provide: CategoriesApiService,
          useValue: {
            list: () =>
              of({
                count: 2,
                next: null,
                previous: null,
                results: [
                  { id: 'c1', name: 'Servicios básicos', active: true, createdAt: '', updatedAt: '' },
                  { id: 'c2', name: 'Sueldos y salarios', active: true, createdAt: '', updatedAt: '' },
                ],
              }),
          },
        },
        { provide: AccountingApiService, useValue: { listAccounts: () => of(ALL_ACCOUNTS) } },
      ],
    });
    const fixture = TestBed.createComponent(ExpenseSettingsComponent);
    fixture.detectChanges();
    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(get).toHaveBeenCalledOnceWith('expenses');
    expect(text).toContain('Configuración de Gastos');
    expect(text).toContain('Cuenta de gasto por categoría');
    expect(text).toContain('Servicios básicos');
    expect(text).toContain('Sueldos y salarios');
  });
});
