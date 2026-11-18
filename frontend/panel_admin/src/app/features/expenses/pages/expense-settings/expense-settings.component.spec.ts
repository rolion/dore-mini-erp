import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Page } from '../../../../shared/models/page';
import { AccountingApiService } from '../../../accounting/services/accounting-api.service';
import { PostingConfigApiService } from '../../../accounting/services/posting-config-api.service';
import { ALL_ACCOUNTS, expensesConfig } from '../../../accounting/testing/posting-fixtures';
import { ExpenseCategory } from '../../models/category';
import { CategoriesApiService } from '../../services/categories-api.service';
import { ExpenseSettingsComponent } from './expense-settings.component';

const category = (id: string, name: string, active = true): ExpenseCategory => ({ id, name, active, createdAt: '', updatedAt: '' });
const page = (results: ExpenseCategory[], next: string | null = null): Page<ExpenseCategory> => ({ count: results.length, next, previous: null, results });

describe('ExpenseSettingsComponent', () => {
  let list: jasmine.Spy;
  let get: jasmine.Spy;

  function create(): ComponentFixture<ExpenseSettingsComponent> {
    get = jasmine.createSpy('get').and.returnValue(of(expensesConfig()));
    TestBed.configureTestingModule({
      imports: [ExpenseSettingsComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: PostingConfigApiService, useValue: { get } },
        { provide: CategoriesApiService, useValue: { list } },
        { provide: AccountingApiService, useValue: { listAccounts: () => of(ALL_ACCOUNTS) } },
      ],
    });
    const fixture = TestBed.createComponent(ExpenseSettingsComponent);
    fixture.detectChanges();
    return fixture;
  }

  const text = (fixture: ComponentFixture<unknown>) => (fixture.nativeElement as HTMLElement).textContent ?? '';

  it('shows the account configuration of the Expenses module with its categories (AC-13)', () => {
    list = jasmine.createSpy('list').and.returnValue(of(page([category('c1', 'Servicios básicos'), category('c2', 'Sueldos y salarios')])));
    const fixture = create();
    expect(get).toHaveBeenCalledOnceWith('expenses');
    expect(text(fixture)).toContain('Configuración de Gastos');
    expect(text(fixture)).toContain('Cuenta de gasto por categoría');
    expect(text(fixture)).toContain('Servicios básicos');
    expect(text(fixture)).toContain('Sueldos y salarios');
  });

  it('loads every page of categories so none is left out of the configuration (REV-09)', () => {
    list = jasmine.createSpy('list').and.callFake((params: { page: number }) =>
      of(params.page === 1 ? page([category('c1', 'Primera')], 'next-url') : page([category('c2', 'Segunda página')])),
    );
    const fixture = create();
    expect(list).toHaveBeenCalledTimes(2);
    expect(list.calls.argsFor(0)[0]).toEqual({ pageSize: 100, page: 1 });
    expect(list.calls.argsFor(1)[0]).toEqual({ pageSize: 100, page: 2 });
    expect(fixture.componentInstance.categories?.map((c) => c.name)).toEqual(['Primera', 'Segunda página']);
    expect(text(fixture)).toContain('Segunda página');
  });

  it('shows an error with retry when the categories cannot be loaded, and recovers (REV-13)', () => {
    list = jasmine.createSpy('list').and.returnValue(throwError(() => new Error('boom')));
    const fixture = create();
    expect(text(fixture)).toContain('No se pudieron cargar las categorías de gasto.');
    expect(fixture.nativeElement.querySelector('app-posting-config-panel')).toBeNull();
    list.and.returnValue(of(page([category('c1', 'Servicios básicos')])));
    Array.from<HTMLButtonElement>(fixture.nativeElement.querySelectorAll('button')).find((b) => b.textContent?.trim() === 'Reintentar')?.click();
    fixture.detectChanges();
    expect(fixture.nativeElement.querySelector('app-posting-config-panel')).not.toBeNull();
    expect(text(fixture)).toContain('Servicios básicos');
  });
});
