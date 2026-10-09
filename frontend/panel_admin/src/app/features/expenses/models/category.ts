export const CATEGORY_NAME_MAX_LENGTH = 100;

export interface ExpenseCategory {
  id: string;
  name: string;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface ExpenseCategoryDto {
  id: string;
  name: string;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CategoryListParams {
  active?: boolean;
  search?: string;
  /** Página base 1. */
  page?: number;
  pageSize?: number;
}
