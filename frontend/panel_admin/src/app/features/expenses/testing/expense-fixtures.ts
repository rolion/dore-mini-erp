import { Page } from '../../../shared/models/page';
import { ExpenseCategory } from '../models/category';
import { Expense } from '../models/expense';
import { ExpensePage } from '../services/expenses-api.service';

export function makeCategory(overrides: Partial<ExpenseCategory> = {}): ExpenseCategory {
  return {
    id: 'cat-1',
    name: 'Materia prima',
    active: true,
    createdAt: '2026-10-09T10:00:00Z',
    updatedAt: '2026-10-09T10:00:00Z',
    ...overrides,
  };
}

export function makeExpense(overrides: Partial<Expense> = {}): Expense {
  return {
    id: 'exp-1',
    description: 'Harina de maíz',
    amount: '120.50',
    expenseDate: '2026-10-05',
    category: { id: 'cat-1', name: 'Materia prima', active: true },
    paymentMethod: 'CASH',
    supplierName: 'Molino Sur',
    notes: 'Compra semanal',
    status: 'ACTIVE',
    voidedAt: null,
    createdAt: '2026-10-05T10:00:00Z',
    updatedAt: '2026-10-05T11:00:00Z',
    ...overrides,
  };
}

export function expensePage(results: Expense[], totalAmount = '0.00', count = results.length): ExpensePage {
  return { count, next: null, previous: null, results, totalAmount };
}

export function categoryPage(results: ExpenseCategory[], count = results.length): Page<ExpenseCategory> {
  return { count, next: null, previous: null, results };
}
