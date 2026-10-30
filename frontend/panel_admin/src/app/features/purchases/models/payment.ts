export type PaymentMethod = 'CASH' | 'QR' | 'BANK_TRANSFER' | 'CARD' | 'OTHER';
export type PaymentRecordStatus = 'confirmed' | 'voided';

export const PAYMENT_METHOD_LABELS: Readonly<Record<PaymentMethod, string>> = {
  CASH: 'Efectivo',
  QR: 'QR',
  BANK_TRANSFER: 'Transferencia',
  CARD: 'Tarjeta',
  OTHER: 'Otro',
};

export const PAYMENT_METHODS: readonly PaymentMethod[] = ['CASH', 'QR', 'BANK_TRANSFER', 'CARD', 'OTHER'];

export const PAYMENT_STATUS_RECORD_LABELS: Readonly<Record<PaymentRecordStatus, string>> = {
  confirmed: 'Confirmado',
  voided: 'Anulado',
};

export interface Payment {
  id: string;
  /** Referencia interna provisional (`PAG-XXXXXXXX`). */
  reference: string;
  /** Texto decimal con 2 decimales. */
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
  status: PaymentRecordStatus;
  userName: string;
  createdAt: string;
}

/** Lo que se envía al registrar; `paymentId` se genera al abrir el diálogo y se reutiliza en cada reintento. */
export interface PaymentInput {
  paymentId: string;
  amount: string;
  paymentMethod: PaymentMethod;
  paymentDate: string;
}

/** Forma de respuesta de la API (snake_case). */
export interface PaymentDto {
  id: string;
  reference: string;
  amount: string;
  payment_method: PaymentMethod;
  payment_date: string;
  status: PaymentRecordStatus;
  user_name: string;
  created_at: string;
}

export interface PaymentFieldErrors {
  amount?: string;
  paymentMethod?: string;
  paymentDate?: string;
}

export class PaymentApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
    readonly fieldErrors: PaymentFieldErrors = {},
  ) {
    super(message);
    this.name = 'PaymentApiError';
  }
}
