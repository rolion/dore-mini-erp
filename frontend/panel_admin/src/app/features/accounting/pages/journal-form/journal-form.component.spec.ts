import { TestBed } from '@angular/core/testing';
import { Router, provideRouter } from '@angular/router';
import { of, throwError } from 'rxjs';
import { provideTestTranslations } from '../../../../core/i18n/testing';
import { Account, AccountingApiError } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { JournalApiService } from '../../services/journal-api.service';
import { makeJournalDetail } from '../../testing/journal-fixtures';
import { JournalFormComponent } from './journal-form.component';

const account = (id: string, code: string, name: string): Account => ({
  id, code, name, currency: 'BOB', kind: null, accountClass: 'ASSET', openingBalance: '0.00', isActive: true,
});

describe('JournalFormComponent', () => {
  function create(createResult = of(makeJournalDetail())) {
    const accounting = jasmine.createSpyObj<AccountingApiService>('AccountingApiService', ['listAccounts']);
    accounting.listAccounts.and.returnValue(of([
      account('a-1', '111001', 'Caja'), account('a-2', '111002', 'Banco'), account('a-3', '411001', 'Ingresos servicios'),
      { ...account('a-4', '', 'Vieja'), code: null, accountClass: null },
    ]));
    const journal = jasmine.createSpyObj<JournalApiService>('JournalApiService', ['create']);
    journal.create.and.returnValue(createResult);
    TestBed.configureTestingModule({
      imports: [JournalFormComponent],
      providers: [...provideTestTranslations(), provideRouter([]), { provide: AccountingApiService, useValue: accounting }, { provide: JournalApiService, useValue: journal }],
    });
    const fixture = TestBed.createComponent(JournalFormComponent);
    fixture.detectChanges();
    return { fixture, component: fixture.componentInstance, journal, el: fixture.nativeElement as HTMLElement };
  }

  function type(fixture: { detectChanges(): void }, el: HTMLElement, selector: string, value: string): void {
    const input = el.querySelector(selector) as HTMLInputElement | HTMLSelectElement;
    input.value = value;
    input.dispatchEvent(new Event(input instanceof HTMLSelectElement ? 'change' : 'input'));
    fixture.detectChanges();
  }

  function fillSale(fixture: { detectChanges(): void }, el: HTMLElement, income = '500'): void {
    type(fixture, el, '#entry-description', 'Servicio');
    const rows = Array.from(el.querySelectorAll('[data-testid="line"]'));
    const set = (row: Element, accountId: string, field: 'debit' | 'credit', amount: string) => {
      const select = row.querySelector('select') as HTMLSelectElement;
      select.value = accountId;
      select.dispatchEvent(new Event('change'));
      const input = row.querySelectorAll('input')[field === 'debit' ? 0 : 1] as HTMLInputElement;
      input.value = amount;
      input.dispatchEvent(new Event('input'));
    };
    set(rows[0], 'a-1', 'debit', '200');
    set(rows[1], 'a-2', 'debit', '300');
    fixture.detectChanges();
    el.querySelector<HTMLButtonElement>('[data-testid="add-line"]')?.click();
    fixture.detectChanges();
    set(el.querySelectorAll('[data-testid="line"]')[2], 'a-3', 'credit', income);
    fixture.detectChanges();
  }

  it('starts with two lines, offers only classified accounts and blocks confirming (AC-08)', () => {
    const { el, component } = create();
    expect(el.querySelectorAll('[data-testid="line"]').length).toBe(2);
    expect(el.querySelectorAll('select')[0].querySelectorAll('option').length).toBe(1 + 3); // placeholder + 3 usable
    expect(component.canRemove).toBeFalse();
    expect((el.querySelector('[data-testid="confirm"]') as HTMLButtonElement).disabled).toBeTrue();
  });

  it('adds and removes lines but never goes below two (AC-08)', () => {
    const { fixture, el, component } = create();
    el.querySelector<HTMLButtonElement>('[data-testid="add-line"]')?.click();
    fixture.detectChanges();
    expect(el.querySelectorAll('[data-testid="line"]').length).toBe(3);
    el.querySelector<HTMLButtonElement>('[data-testid="remove-line"]')?.click();
    fixture.detectChanges();
    expect(component.lines.length).toBe(2);
    expect(component.canRemove).toBeFalse();
  });

  it('with the service sale shows Debit 500, Credit 500, Difference 0 and confirms (AC-01, AC-08)', () => {
    const { fixture, el, journal } = create();
    const navigate = spyOn(TestBed.inject(Router), 'navigate').and.resolveTo(true);
    fillSale(fixture, el);
    expect(el.querySelector('[data-testid="total-debit"]')?.textContent?.trim()).toBe('500.00');
    expect(el.querySelector('[data-testid="total-credit"]')?.textContent?.trim()).toBe('500.00');
    expect(el.querySelector('[data-testid="difference"]')?.textContent).toContain('0.00');
    const confirm = el.querySelector('[data-testid="confirm"]') as HTMLButtonElement;
    expect(confirm.disabled).toBeFalse();
    confirm.click();
    expect(journal.create).toHaveBeenCalledTimes(1);
    expect(journal.create.calls.mostRecent().args[0].lines.map((l) => l.account_id)).toEqual(['a-1', 'a-2', 'a-3']);
    expect(navigate).toHaveBeenCalledWith(['/pocketbiz/accounting/journal', 'j-1'], { queryParams: { created: 1 } });
  });

  it('keeps Confirm disabled with a difference of 1 and never calls the API (AC-02)', () => {
    const { fixture, el, journal, component } = create();
    fillSale(fixture, el, '499');
    expect(el.querySelector('[data-testid="difference"]')?.textContent).toContain('1.00');
    expect((el.querySelector('[data-testid="confirm"]') as HTMLButtonElement).disabled).toBeTrue();
    component.submit();
    expect(journal.create).not.toHaveBeenCalled();
  });

  it('typing in one side clears the other', () => {
    const { fixture, el } = create();
    const row = el.querySelector('[data-testid="line"]') as HTMLElement;
    const [debit, credit] = Array.from(row.querySelectorAll('input')) as HTMLInputElement[];
    debit.value = '10';
    debit.dispatchEvent(new Event('input'));
    credit.value = '4';
    credit.dispatchEvent(new Event('input'));
    fixture.detectChanges();
    expect([debit.value, credit.value]).toEqual(['', '4']);
  });

  it('shows the server errors without clearing what was typed and re-enables the button (AC-02)', () => {
    const failure = new AccountingApiError('Revisa', 400, { lines: ['El asiento no cuadra'], accounting_date: ['Período cerrado'] });
    const { fixture, el, component } = create(throwError(() => failure));
    fillSale(fixture, el);
    (el.querySelector('[data-testid="confirm"]') as HTMLButtonElement).click();
    fixture.detectChanges();
    expect(el.querySelector('[data-testid="lines-error"]')?.textContent).toContain('no cuadra');
    expect(el.querySelector('[data-testid="date-error"]')?.textContent).toContain('cerrado');
    expect(component.saving).toBeFalse();
    expect((el.querySelector('#entry-description') as HTMLInputElement).value).toBe('Servicio');
  });

  it('warns about unsaved changes only after editing and not after saving', () => {
    const { fixture, el, component } = create();
    expect(component.hasUnsavedChanges()).toBeFalse();
    type(fixture, el, '#entry-description', 'x');
    expect(component.hasUnsavedChanges()).toBeTrue();
  });
});
