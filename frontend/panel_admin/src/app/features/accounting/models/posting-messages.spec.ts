import { TestBed } from '@angular/core/testing';
import { TranslateService } from '@ngx-translate/core';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { AppLanguage } from '../../../core/i18n/language.config';
import { PostingIssue } from './posting-config';
import { issueText, problemText } from './posting-messages';

const issue = (overrides: Partial<PostingIssue>): PostingIssue => ({
  code: 'role_unconfigured',
  role: 'RECEIVABLE',
  subject: 'Cuentas por cobrar',
  module: 'sales',
  message: 'Falta configurar la cuenta «Cuentas por cobrar». Configúrela en Ventas › Configuración › Asientos automáticos.',
  params: {},
  problem: null,
  ...overrides,
});

describe('posting messages (REV-05)', () => {
  const use = (lang: AppLanguage) => {
    TestBed.configureTestingModule({ providers: provideTestTranslations(lang) });
    TestBed.inject(TranslateService);
  };

  it('translates a missing role in the active language, naming where to fix it', () => {
    use('en');
    expect(issueText(issue({}))).toBe('The account “Accounts receivable” is not configured. Set it in Sales › Settings › Automatic entries.');
  });

  it('translates in Spanish and Portuguese too', () => {
    use('es');
    expect(issueText(issue({}))).toBe('Falta configurar la cuenta «Cuentas por cobrar». Configúrela en Ventas › Configuración › Asientos automáticos.');
    TestBed.resetTestingModule();
    use('pt');
    expect(issueText(issue({}))).toContain('Falta configurar a conta «Contas a receber». Configure-a em Vendas › Configuração › Lançamentos automáticos.');
  });

  it('translates method and category issues with their names', () => {
    use('en');
    expect(issueText(issue({ code: 'method_unconfigured', role: 'MONEY', params: { method: 'Efectivo' } }))).toBe(
      'The Asset account of the method “Efectivo” is missing. Set it in Sales › Settings › Automatic entries.',
    );
    expect(issueText(issue({ code: 'category_unconfigured', module: 'expenses', params: { category: 'Luz' } }))).toContain('category “Luz” is missing');
    expect(issueText(issue({ code: 'category_unconfigured', module: 'expenses', params: { category: '' } }))).toContain('of the category is missing');
    expect(issueText(issue({ code: 'category_required' }))).toBe('Provide the expense category of the operation.');
  });

  it('translates an invalid account with its structured cause, class names and the subject', () => {
    use('en');
    const wrongClass = { code: 'wrong_class', params: { account: 'Gastos', actual: 'EXPENSE', required: 'INCOME' }, message: 'x' };
    expect(problemText(wrongClass)).toBe('The account “Gastos” is Expense; a Income account is required.');
    const text = issueText(issue({ code: 'account_invalid', role: 'MONEY', subject: 'Caja o banco del método de pago · Efectivo', problem: wrongClass }));
    expect(text).toContain('Fix “Asset account of the payment method · Efectivo” in Sales › Settings › Automatic entries.');
  });

  it('falls back to the server message when the code is unknown or missing', () => {
    use('en');
    expect(issueText(issue({ code: 'something_new', message: 'Mensaje del servidor' }))).toBe('Mensaje del servidor');
    expect(problemText({ code: 'brand_new', params: {}, message: 'Respaldo' })).toBe('Respaldo');
    expect(problemText(null, 'sin causa')).toBe('sin causa');
  });
});
