/** Tipos que se pueden elegir al registrarse; `general` solo lo tienen las empresas anteriores al tipo. */
export const REGISTERABLE_COMPANY_TYPES = ['compraventa', 'servicios', 'odontologia'] as const;
export type RegisterableCompanyType = (typeof REGISTERABLE_COMPANY_TYPES)[number];
export type CompanyType = RegisterableCompanyType | 'general';

export interface UserCompany {
  id: string;
  name: string;
  /** Ausente en sesiones guardadas antes del tipo de empresa: se trata como `general`. */
  type?: string;
}

export class User {
  id!: number;
  username!: string;
  firstName!: string;
  lastName!: string;
  token!: string;
  /** Ausentes en sesiones guardadas antes del aislamiento por empresa. */
  role?: string;
  company?: UserCompany;
}

/** Respuesta de login y de registro: misma forma (sesión iniciada). */
export interface LoginResponse {
  token: string;
  user: {
    id: number;
    username: string;
    first_name: string;
    last_name: string;
    role?: string;
    company?: UserCompany | null;
  };
}

export interface RegisterInput {
  companyName: string;
  companyType: RegisterableCompanyType;
  username: string;
  firstName: string;
  lastName: string;
  email: string;
  password: string;
}

export type RegisterField = keyof RegisterInput;
