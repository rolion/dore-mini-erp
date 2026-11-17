import { Account } from '../models/accounting';
import { PostingCategory, PostingConfig, PostingModule } from '../models/posting-config';

export const caja: Account = { id: 'm1', name: 'Caja', code: '110101', currency: 'BOB', kind: 'CASH', accountClass: 'ASSET', openingBalance: '0.00', isActive: true };
export const banco: Account = { id: 'm2', name: 'Banco', code: '110102', currency: 'BOB', kind: 'BANK', accountClass: 'ASSET', openingBalance: '0.00', isActive: true };
export const porCobrar: Account = { id: 'r1', name: 'Por cobrar', code: '112001', currency: 'BOB', kind: null, accountClass: 'ASSET', openingBalance: '0.00', isActive: true };
export const ingresos: Account = { id: 'i1', name: 'Ingresos por ventas', code: '410001', currency: 'BOB', kind: null, accountClass: 'INCOME', openingBalance: '0.00', isActive: true };
export const gastoLuz: Account = { id: 'g1', name: 'Gasto de luz', code: '510001', currency: 'BOB', kind: null, accountClass: 'EXPENSE', openingBalance: '0.00', isActive: true };
export const ALL_ACCOUNTS: Account[] = [caja, banco, porCobrar, ingresos, gastoLuz];

/** Configuración de Ventas: todo sin configurar salvo lo que se pase en `overrides`. */
export function salesConfig(overrides: Partial<PostingConfig> = {}): PostingConfig {
  return {
    module: 'sales',
    moduleLabel: 'Ventas',
    accountingEnabled: true,
    ready: false,
    events: [
      {
        code: 'SALE_RECOGNITION',
        label: 'Reconocer una venta',
        issues: [
          { code: 'role_unconfigured', role: 'RECEIVABLE', subject: 'Cuentas por cobrar', module: 'sales', message: 'Falta configurar la cuenta «Cuentas por cobrar». Configúrela en Ventas › Configuración › Asientos automáticos.', params: {}, problem: null },
        ],
        preview: [
          { side: 'DEBIT', role: 'RECEIVABLE', label: 'Cuentas por cobrar', account: null, status: 'missing' },
          { side: 'CREDIT', role: 'SALES_INCOME', label: 'Ingresos por ventas', account: null, status: 'missing' },
        ],
      },
      {
        code: 'SALE_PAYMENT',
        label: 'Cobrar una venta',
        issues: [],
        preview: [
          { side: 'DEBIT', role: 'MONEY', label: 'Caja o banco', account: null, status: 'by_method' },
          { side: 'CREDIT', role: 'RECEIVABLE', label: 'Cuentas por cobrar', account: null, status: 'missing' },
        ],
      },
    ],
    roles: [
      { role: 'RECEIVABLE', label: 'Cuentas por cobrar', accountClass: 'ASSET', account: null, issue: null, problem: null, sharedWith: [{ module: 'receivables', label: 'Cobros' }] },
      { role: 'SALES_INCOME', label: 'Ingresos por ventas', accountClass: 'INCOME', account: null, issue: null, problem: null, sharedWith: [] },
    ],
    methods: [
      { code: 'CASH', label: 'Efectivo', isActive: true, account: null, issue: null, problem: null },
      { code: 'QR', label: 'QR', isActive: true, account: null, issue: null, problem: null },
    ],
    categories: [],
    ...overrides,
  };
}

export function expensesConfig(module: PostingModule = 'expenses'): PostingConfig {
  return {
    module,
    moduleLabel: 'Gastos',
    accountingEnabled: true,
    ready: false,
    events: [
      {
        code: 'EXPENSE_RECORD',
        label: 'Registrar un gasto',
        issues: [],
        preview: [
          { side: 'DEBIT', role: 'EXPENSE_BY_CATEGORY', label: 'Cuenta de gasto', account: null, status: 'by_category' },
          { side: 'CREDIT', role: 'MONEY', label: 'Caja o banco', account: null, status: 'by_method' },
        ],
      },
    ],
    roles: [],
    methods: [{ code: 'CASH', label: 'Efectivo', isActive: true, account: null, issue: null, problem: null }],
    categories: [],
  };
}

/** Categorías de Gastos que su pantalla entrega al panel (Contabilidad no las conoce). */
export const EXPENSE_CATEGORIES: PostingCategory[] = [
  { id: 'c1', name: 'Servicios básicos', isActive: true },
  { id: 'c2', name: 'Alquiler', isActive: false },
  { id: 'c3', name: 'Pago a proveedores', isActive: true },
];
