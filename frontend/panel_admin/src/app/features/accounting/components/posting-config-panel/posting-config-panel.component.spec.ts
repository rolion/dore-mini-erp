import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { AppLanguage } from '../../../../core/i18n/language.config';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError } from '../../models/accounting';
import { PostingCategory, PostingConfig, PostingModule } from '../../models/posting-config';
import { AccountingApiService } from '../../services/accounting-api.service';
import { PostingConfigApiService } from '../../services/posting-config-api.service';
import { ALL_ACCOUNTS, EXPENSE_CATEGORIES, caja, expensesConfig, gastoLuz, ingresos, salesConfig } from '../../testing/posting-fixtures';
import { PostingConfigPanelComponent } from './posting-config-panel.component';

describe('PostingConfigPanelComponent', () => {
  let api: jasmine.SpyObj<PostingConfigApiService>;
  let accounting: jasmine.SpyObj<AccountingApiService>;

  function create(module: PostingModule, config: PostingConfig, accounts: Account[] = ALL_ACCOUNTS, categories: PostingCategory[] = [], lang: AppLanguage = 'es'): ComponentFixture<PostingConfigPanelComponent> {
    api = jasmine.createSpyObj<PostingConfigApiService>('PostingConfigApiService', ['get', 'setRoleAccount', 'setCategoryAccount']);
    accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'configureMethod']);
    api.get.and.returnValue(of(config));
    accounting.listAccounts.and.returnValue(of(accounts));
    TestBed.configureTestingModule({
      imports: [PostingConfigPanelComponent],
      providers: [
        ...provideTestTranslations(lang),
        provideRouter([]),
        { provide: PostingConfigApiService, useValue: api },
        { provide: AccountingApiService, useValue: accounting },
      ],
    });
    const fixture = TestBed.createComponent(PostingConfigPanelComponent);
    fixture.componentRef.setInput('module', module);
    fixture.componentRef.setInput('categories', categories);
    fixture.detectChanges();
    return fixture;
  }

  const el = (fixture: ComponentFixture<unknown>) => fixture.nativeElement as HTMLElement;
  const select = (fixture: ComponentFixture<unknown>, key: string) => el(fixture).querySelector<HTMLSelectElement>(`[id="sel-${key}"]`)!;
  const choose = (fixture: ComponentFixture<unknown>, key: string, value: string) => {
    const field = select(fixture, key);
    field.value = value;
    field.dispatchEvent(new Event('change'));
    fixture.detectChanges();
  };

  it('shows only the events of its module with a Debit/Credit preview (AC-12)', () => {
    const fixture = create('sales', salesConfig());
    const events = el(fixture).querySelectorAll('[data-testid^="event-"]');
    expect(events.length).toBe(3);
    expect(el(fixture).textContent).toContain('Reconocer la entrega de un pedido');
    expect(el(fixture).textContent).toContain('Cobrar una venta');
    expect(el(fixture).textContent).not.toContain('Registrar un gasto');
    expect(el(fixture).textContent).toContain('Cobrar un pedido por adelantado');
    const delivery = el(fixture).querySelector('[data-testid="event-SALE_DELIVERY"]')!.textContent ?? '';
    expect(delivery).toContain('Debe');
    expect(delivery).toContain('Haber');
    expect(delivery).toContain('Sin configurar');
    expect(delivery).toContain('Anticipos de clientes');  // la entrega aplica anticipos: segunda línea de Debe
    expect(events[2].textContent).toContain('Según el método de pago');
  });

  it('recalculates the preview as soon as an account is chosen, before saving (AC-12)', () => {
    const fixture = create('sales', salesConfig());
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    const first = el(fixture).querySelector('[data-testid="event-SALE_DELIVERY"]')!.textContent ?? '';
    expect(first).toContain('410001 · Ingresos por ventas');
    expect(api.setRoleAccount).not.toHaveBeenCalled();
  });

  it('lists only active BOB accounts of the right classification for each role and Asset accounts for methods, whatever their type', () => {
    const inactive: Account = { ...ingresos, id: 'i2', name: 'Ingresos viejos', isActive: false };
    const usd: Account = { ...ingresos, id: 'i3', name: 'Ingresos USD', currency: 'USD' };
    const fixture = create('sales', salesConfig(), [...ALL_ACCOUNTS, inactive, usd]);
    const names = (key: string) => Array.from(select(fixture, key).options).map((o) => o.textContent?.trim());
    expect(names('role:SALES_INCOME')).toEqual(['Sin cuenta', '410001 · Ingresos por ventas']);
    expect(names('role:CUSTOMER_ADVANCES')).toEqual(['Sin cuenta', '210001 · Anticipos de clientes']);
    expect(names('role:RECEIVABLE')).toEqual(['Sin cuenta', '110101 · Caja', '110102 · Banco', '112001 · Por cobrar']);
    expect(names('method:CASH')).toEqual(['Sin cuenta', '110101 · Caja', '110102 · Banco', '112001 · Por cobrar']);
  });

  it('saves a role, refreshes the configuration and confirms (AC-02)', () => {
    const fixture = create('sales', salesConfig());
    api.setRoleAccount.and.returnValue(of({ role: 'SALES_INCOME', label: 'x', accountClass: 'INCOME', account: { id: ingresos.id, code: '410001', name: 'x', isActive: true }, issue: null, problem: null, sharedWith: [] }));
    const updated = salesConfig();
    updated.roles[2] = { ...updated.roles[2], account: { id: ingresos.id, code: '410001', name: 'Ingresos por ventas', isActive: true } };
    api.get.and.returnValue(of(updated));
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    const save = el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-role:SALES_INCOME"] button')!;
    expect(save.disabled).toBeFalse();
    save.click();
    fixture.detectChanges();
    expect(api.setRoleAccount).toHaveBeenCalledOnceWith('SALES_INCOME', ingresos.id);
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(fixture.componentInstance.roleRows[2].saving).toBeFalse();
    expect(el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"]')!.textContent).toContain('Guardado');
  });

  it('shows the server field error under the row and keeps the selection (AC-03)', () => {
    const fixture = create('sales', salesConfig());
    api.setRoleAccount.and.returnValue(throwError(() => new AccountingApiError('Revisa', 400, { accountId: ['La cuenta «X» es de Gastos; se requiere una cuenta de Ingresos.'] })));
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-role:SALES_INCOME"] button')!.click();
    fixture.detectChanges();
    const row = el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"]')!;
    expect(row.querySelector('[role="alert"]')?.textContent).toContain('se requiere una cuenta de Ingresos');
    expect(select(fixture, 'role:SALES_INCOME').value).toBe(ingresos.id);
  });

  it('saves a payment method through the shared method mapping, keeping its active state', () => {
    const fixture = create('sales', salesConfig());
    accounting.configureMethod.and.returnValue(of({ code: 'CASH', label: 'Efectivo', isActive: true, account: caja }));
    choose(fixture, 'method:CASH', caja.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-method:CASH"] button')!.click();
    expect(accounting.configureMethod).toHaveBeenCalledOnceWith('CASH', caja.id, true);
  });

  it('warns about missing configuration when Accounting is enabled, listing each fix (AC-12)', () => {
    const fixture = create('sales', salesConfig());
    const warning = el(fixture).querySelector('[data-testid="posting-missing"]')!;
    expect(warning.textContent).toContain('Falta configurar 1 cuenta(s)');
    expect(warning.textContent).toContain('Ventas › Configuración › Asientos automáticos');
    expect(el(fixture).textContent).toContain('Los cambios aplican solo a operaciones nuevas');
  });

  it('explains instead of warning when Accounting is disabled (AC-12)', () => {
    const fixture = create('sales', salesConfig({ accountingEnabled: false }));
    expect(el(fixture).querySelector('[data-testid="posting-disabled"]')).not.toBeNull();
    expect(el(fixture).querySelector('[data-testid="posting-missing"]')).toBeNull();
  });

  it('shows the ready state when nothing is missing', () => {
    const fixture = create('sales', salesConfig({ ready: true, events: [] }));
    expect(el(fixture).querySelector('[data-testid="posting-ready"]')).not.toBeNull();
  });

  it('marks a saved account that is no longer valid and still lets the person fix it', () => {
    const config = salesConfig();
    config.roles[2] = { ...config.roles[2], account: { id: 'old', code: '4100', name: 'Vieja', isActive: false }, issue: 'La cuenta «Vieja» está deshabilitada; elija otra o actívela en Cuentas.', problem: null };
    config.events[1].preview[2] = { side: 'CREDIT', role: 'SALES_INCOME', label: 'x', account: { id: 'old', code: '4100', name: 'Vieja', isActive: false }, status: 'invalid' };
    const fixture = create('sales', config);
    expect(el(fixture).querySelector('[data-testid="event-SALE_DELIVERY"]')!.textContent).toContain('4100 · Vieja · ya no es válida');
    expect(el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"]')!.textContent).toContain('está deshabilitada');
  });

  it('keeps a saved account that is no longer eligible visible and marked in the selector (REV-11)', () => {
    const config = salesConfig();
    config.roles[2] = { ...config.roles[2], account: { id: 'old', code: '4100', name: 'Vieja', isActive: false }, issue: 'La cuenta «Vieja» está deshabilitada.', problem: null };
    const fixture = create('sales', config);
    const field = select(fixture, 'role:SALES_INCOME');
    expect(field.value).toBe('old');
    expect(field.selectedOptions[0].textContent).toContain('4100 · Vieja · ya no es válida');
  });

  it('reports a category whose saved account stopped being valid, by name (REV-13)', () => {
    const config = expensesConfig();
    config.categories = [{ categoryId: 'c1', account: { id: 'g9', code: '5100', name: 'Gasto luz', isActive: false }, issue: 'La cuenta «Gasto luz» está deshabilitada; elija otra o actívela en Cuentas.', problem: null }];
    const fixture = create('expenses', config, ALL_ACCOUNTS, EXPENSE_CATEGORIES);
    const warning = el(fixture).querySelector('[data-testid="posting-missing"]')!.textContent ?? '';
    expect(warning).toContain('«Gasto luz» está deshabilitada');
    expect(select(fixture, 'category:c1').selectedOptions[0].textContent).toContain('ya no es válida');
  });

  it('shows the missing-configuration notices and row problems in the active language (REV-05)', () => {
    const config = salesConfig();
    config.roles[2] = {
      ...config.roles[2],
      account: { id: 'old', code: '4100', name: 'Vieja', isActive: false },
      issue: 'La cuenta «Vieja» está deshabilitada; elija otra o actívela en Cuentas.',
      problem: { code: 'account_inactive', params: { account: 'Vieja' } },
    };
    const english = create('sales', config, ALL_ACCOUNTS, [], 'en');
    const warning = el(english).querySelector('[data-testid="posting-missing"]')!.textContent ?? '';
    expect(warning).toContain('The account “Accounts receivable” is not configured. Set it in Sales › Settings › Automatic entries.');
    expect(warning).not.toContain('Falta configurar');
    expect(el(english).querySelector('[data-testid="row-role:SALES_INCOME"]')!.textContent).toContain(
      'The account “Vieja” is disabled; choose another one or enable it in Accounts.',
    );
  });

  it('shows the 400 cause of a rejected account in the active language (REV-05)', () => {
    const fixture = create('sales', salesConfig(), ALL_ACCOUNTS, [], 'pt');
    api.setRoleAccount.and.returnValue(
      throwError(() => new AccountingApiError('Revisa', 400, { accountId: ['x'] }, null, [], { code: 'wrong_class', params: { account: 'Gastos', actual: 'EXPENSE', required: 'INCOME' } })),
    );
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-role:SALES_INCOME"] button')!.click();
    fixture.detectChanges();
    expect(el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"] [role="alert"]')!.textContent).toContain(
      'A conta «Gastos» é de Despesas; é necessária uma conta de Receitas.',
    );
  });

  it('shows module names, shared modules and payment methods in the active language (REV-14)', () => {
    const fixture = create('sales', salesConfig(), ALL_ACCOUNTS, [], 'en');
    const text = el(fixture).textContent ?? '';
    expect(text).toContain('Choose the accounts Sales will use');
    expect(el(fixture).querySelector('[data-testid="row-role:RECEIVABLE"]')!.textContent).toContain('Shared with: Collections.');
    expect(el(fixture).querySelector('[data-testid="row-method:CASH"]')!.textContent).toContain('Cash');
    expect(text).not.toContain('Ventas');
    expect(text).not.toContain('Efectivo');
  });

  it('keeps a save error as its cause so it is re-translated when the language changes (REV-15)', () => {
    const fixture = create('sales', salesConfig(), ALL_ACCOUNTS);
    api.setRoleAccount.and.returnValue(
      throwError(() => new AccountingApiError('Revisa', 400, { accountId: ['x'] }, null, [], { code: 'account_inactive', params: { account: 'Vieja' } })),
    );
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-role:SALES_INCOME"] button')!.click();
    fixture.detectChanges();
    const alert = () => el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"] [role="alert"]')!.textContent ?? '';
    expect(alert()).toContain('está deshabilitada');
    TestBed.inject(TranslateService).use('en');
    fixture.detectChanges();
    expect(alert()).toContain('is disabled; choose another one or enable it in Accounts.');
  });

  it('names each category with an invalid account and folds a long list of notices (REV-16)', () => {
    const categories = Array.from({ length: 12 }, (_, i) => ({ id: `k${i}`, name: `Categoría ${i}`, isActive: true }));
    const config = expensesConfig();
    config.categories = categories.slice(0, 2).map((c) => ({
      categoryId: c.id,
      account: { id: 'g9', code: '5100', name: 'Gasto luz', isActive: false },
      issue: 'La cuenta «Gasto luz» está deshabilitada; elija otra o actívela en Cuentas.',
      problem: { code: 'account_inactive', params: { account: 'Gasto luz' } },
    }));
    const fixture = create('expenses', config, ALL_ACCOUNTS, categories);
    const warning = el(fixture).querySelector('[data-testid="posting-missing"]')!;
    expect(warning.textContent).toContain('Falta configurar 12 cuenta(s)');
    expect(warning.textContent).toContain('Categoría 0');
    expect(warning.textContent).toContain('Categoría 1');
    const more = warning.querySelector('[data-testid="posting-missing-more"]')!;
    expect(more.textContent).toContain('Ver 2 más');
    expect(warning.querySelectorAll('li').length).toBe(12);
  });

  it('tells which other modules share a role', () => {
    const fixture = create('sales', salesConfig());
    expect(el(fixture).querySelector('[data-testid="row-role:RECEIVABLE"]')!.textContent).toContain('Se comparte con: Cobros.');
  });

  it('explains an empty selector and links to accounts (EDGE-04)', () => {
    const fixture = create('sales', salesConfig(), []);
    expect(el(fixture).querySelectorAll('[data-testid="no-options"]').length).toBe(3);
    expect(el(fixture).querySelector('[data-testid="no-money-options"]')).not.toBeNull();
  });

  it('lists the categories of Expenses with expense accounts, dims inactive ones and shows the preview by category (UI-01)', () => {
    const fixture = create('expenses', expensesConfig(), ALL_ACCOUNTS, EXPENSE_CATEGORIES);
    expect(el(fixture).querySelectorAll('[data-testid^="row-category:"]').length).toBe(3);
    const names = Array.from(select(fixture, 'category:c1').options).map((o) => o.textContent?.trim());
    expect(names).toEqual(['Sin cuenta', '510001 · Gasto de luz']);
    expect(el(fixture).querySelector('[data-testid="row-category:c2"]')!.textContent).toContain('Categoría inactiva');
    const preview = el(fixture).querySelector('[data-testid="event-EXPENSE_RECORD"]')!.textContent ?? '';
    expect(preview).toContain('Según la categoría del gasto');
    expect(preview).toContain('Según el método de pago');
    expect(el(fixture).querySelector('[data-testid="posting-roles"]')).toBeNull();
    api.setCategoryAccount.and.returnValue(of({ categoryId: 'c1', account: null, issue: null, problem: null }));
    choose(fixture, 'category:c1', gastoLuz.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-category:c1"] button')!.click();
    expect(api.setCategoryAccount).toHaveBeenCalledOnceWith('c1', gastoLuz.id);
  });

  it('warns about every active category without an expense account, by name, and ignores inactive ones', () => {
    const fixture = create('expenses', { ...expensesConfig(), ready: true }, ALL_ACCOUNTS, EXPENSE_CATEGORIES);
    const warning = el(fixture).querySelector('[data-testid="posting-missing"]')!;
    expect(warning.textContent).toContain('Falta configurar 2 cuenta(s)');
    expect(warning.textContent).toContain('«Servicios básicos»');
    expect(warning.textContent).toContain('«Pago a proveedores»');
    expect(warning.textContent).not.toContain('Alquiler');
  });

  it('shows the configured category account and the ready state once every active category has one', () => {
    const config = expensesConfig();
    config.ready = true;
    config.categories = ['c1', 'c3'].map((id) => ({ categoryId: id, account: { id: gastoLuz.id, code: '510001', name: 'Gasto de luz', isActive: true }, issue: null, problem: null }));
    const fixture = create('expenses', config, ALL_ACCOUNTS, EXPENSE_CATEGORIES);
    expect(select(fixture, 'category:c3').value).toBe(gastoLuz.id);
    expect(el(fixture).querySelector('[data-testid="posting-ready"]')).not.toBeNull();
  });

  it('offers to create a category when there are none', () => {
    const fixture = create('expenses', expensesConfig());
    expect(el(fixture).querySelector('[data-testid="no-categories"]')).not.toBeNull();
  });

  it('shows a retry when the configuration cannot be loaded', () => {
    const fixture = create('sales', salesConfig());
    api.get.and.returnValue(throwError(() => new AccountingApiError('No se pudo conectar', 0)));
    fixture.componentInstance.reload();
    fixture.detectChanges();
    expect(el(fixture).textContent).toContain('No se pudo conectar');
    expect(Array.from(el(fixture).querySelectorAll('button')).some((b) => b.textContent?.trim() === 'Reintentar')).toBeTrue();
  });
});
