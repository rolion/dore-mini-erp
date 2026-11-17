import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError } from '../../models/accounting';
import { PostingConfig, PostingModule } from '../../models/posting-config';
import { AccountingApiService } from '../../services/accounting-api.service';
import { PostingConfigApiService } from '../../services/posting-config-api.service';
import { ALL_ACCOUNTS, caja, expensesConfig, gastoLuz, ingresos, salesConfig } from '../../testing/posting-fixtures';
import { PostingConfigPanelComponent } from './posting-config-panel.component';

describe('PostingConfigPanelComponent', () => {
  let api: jasmine.SpyObj<PostingConfigApiService>;
  let accounting: jasmine.SpyObj<AccountingApiService>;

  function create(module: PostingModule, config: PostingConfig, accounts: Account[] = ALL_ACCOUNTS): ComponentFixture<PostingConfigPanelComponent> {
    api = jasmine.createSpyObj<PostingConfigApiService>('PostingConfigApiService', ['get', 'setRoleAccount', 'setCategoryAccount']);
    accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts', 'configureMethod']);
    api.get.and.returnValue(of(config));
    accounting.listAccounts.and.returnValue(of(accounts));
    TestBed.configureTestingModule({
      imports: [PostingConfigPanelComponent],
      providers: [
        ...provideTestTranslations(),
        provideRouter([]),
        { provide: PostingConfigApiService, useValue: api },
        { provide: AccountingApiService, useValue: accounting },
      ],
    });
    const fixture = TestBed.createComponent(PostingConfigPanelComponent);
    fixture.componentRef.setInput('module', module);
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
    expect(events.length).toBe(2);
    expect(el(fixture).textContent).toContain('Reconocer una venta');
    expect(el(fixture).textContent).toContain('Cobrar una venta');
    expect(el(fixture).textContent).not.toContain('Registrar un gasto');
    const first = events[0].textContent ?? '';
    expect(first).toContain('Debe');
    expect(first).toContain('Haber');
    expect(first).toContain('Sin configurar');
    expect(events[1].textContent).toContain('Según el método de pago');
  });

  it('recalculates the preview as soon as an account is chosen, before saving (AC-12)', () => {
    const fixture = create('sales', salesConfig());
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    const first = el(fixture).querySelector('[data-testid="event-SALE_RECOGNITION"]')!.textContent ?? '';
    expect(first).toContain('410001 · Ingresos por ventas');
    expect(api.setRoleAccount).not.toHaveBeenCalled();
  });

  it('lists only active BOB accounts of the right classification for each role and Asset accounts for methods, whatever their type', () => {
    const inactive: Account = { ...ingresos, id: 'i2', name: 'Ingresos viejos', isActive: false };
    const usd: Account = { ...ingresos, id: 'i3', name: 'Ingresos USD', currency: 'USD' };
    const fixture = create('sales', salesConfig(), [...ALL_ACCOUNTS, inactive, usd]);
    const names = (key: string) => Array.from(select(fixture, key).options).map((o) => o.textContent?.trim());
    expect(names('role:SALES_INCOME')).toEqual(['Sin cuenta', '410001 · Ingresos por ventas']);
    expect(names('role:RECEIVABLE')).toEqual(['Sin cuenta', '110101 · Caja', '110102 · Banco', '112001 · Por cobrar']);
    expect(names('method:CASH')).toEqual(['Sin cuenta', '110101 · Caja', '110102 · Banco', '112001 · Por cobrar']);
  });

  it('saves a role, refreshes the configuration and confirms (AC-02)', () => {
    const fixture = create('sales', salesConfig());
    api.setRoleAccount.and.returnValue(of({ role: 'SALES_INCOME', label: 'x', accountClass: 'INCOME', account: { id: ingresos.id, code: '410001', name: 'x', isActive: true }, issue: null, sharedWith: [] }));
    const updated = salesConfig();
    updated.roles[1] = { ...updated.roles[1], account: { id: ingresos.id, code: '410001', name: 'Ingresos por ventas', isActive: true } };
    api.get.and.returnValue(of(updated));
    choose(fixture, 'role:SALES_INCOME', ingresos.id);
    const save = el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-role:SALES_INCOME"] button')!;
    expect(save.disabled).toBeFalse();
    save.click();
    fixture.detectChanges();
    expect(api.setRoleAccount).toHaveBeenCalledOnceWith('SALES_INCOME', ingresos.id);
    expect(api.get).toHaveBeenCalledTimes(2);
    expect(fixture.componentInstance.roleRows[1].saving).toBeFalse();
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
    config.roles[1] = { ...config.roles[1], account: { id: 'old', code: '4100', name: 'Vieja', isActive: false }, issue: 'La cuenta «Vieja» está deshabilitada; elija otra o actívela en Cuentas.' };
    config.events[0].preview[1] = { side: 'CREDIT', role: 'SALES_INCOME', label: 'x', account: { id: 'old', code: '4100', name: 'Vieja', isActive: false }, status: 'invalid' };
    const fixture = create('sales', config);
    expect(el(fixture).querySelector('[data-testid="event-SALE_RECOGNITION"]')!.textContent).toContain('4100 · Vieja · ya no es válida');
    expect(el(fixture).querySelector('[data-testid="row-role:SALES_INCOME"]')!.textContent).toContain('está deshabilitada');
  });

  it('tells which other modules share a role', () => {
    const fixture = create('sales', salesConfig());
    expect(el(fixture).querySelector('[data-testid="row-role:RECEIVABLE"]')!.textContent).toContain('Se comparte con: Cobros.');
  });

  it('explains an empty selector and links to accounts (EDGE-04)', () => {
    const fixture = create('sales', salesConfig(), []);
    expect(el(fixture).querySelectorAll('[data-testid="no-options"]').length).toBe(2);
    expect(el(fixture).querySelector('[data-testid="no-money-options"]')).not.toBeNull();
  });

  it('lists expense categories with expense accounts, dims inactive ones and shows the preview by category (UI-01)', () => {
    const fixture = create('expenses', expensesConfig());
    const names = Array.from(select(fixture, 'category:c1').options).map((o) => o.textContent?.trim());
    expect(names).toEqual(['Sin cuenta', '510001 · Gasto de luz']);
    expect(el(fixture).querySelector('[data-testid="row-category:c2"]')!.textContent).toContain('Categoría inactiva');
    const preview = el(fixture).querySelector('[data-testid="event-EXPENSE_RECORD"]')!.textContent ?? '';
    expect(preview).toContain('Según la categoría del gasto');
    expect(preview).toContain('Según el método de pago');
    expect(el(fixture).querySelector('[data-testid="posting-roles"]')).toBeNull();
    api.setCategoryAccount.and.returnValue(of({ classificationId: 'c1', name: 'x', isActive: true, account: null, issue: null }));
    choose(fixture, 'category:c1', gastoLuz.id);
    el(fixture).querySelector<HTMLButtonElement>('[data-testid="row-category:c1"] button')!.click();
    expect(api.setCategoryAccount).toHaveBeenCalledOnceWith('c1', gastoLuz.id);
  });

  it('offers to create a category when there are none', () => {
    const fixture = create('expenses', { ...expensesConfig(), categories: [] });
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
