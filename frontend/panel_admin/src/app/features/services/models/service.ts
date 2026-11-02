export interface CatalogService {
  id: string;
  name: string;
  code: string;
  description: string;
  basePrice: string;
  durationMinutes: number;
  specialtyId: string | null;
  specialtyName: string | null;
  active: boolean;
  createdAt: string;
  updatedAt: string;
}

export interface ServiceInput {
  name: string;
  code: string;
  description: string;
  basePrice: string;
  durationMinutes: number;
  specialtyId: string | null;
}

export interface ServiceDto {
  id: string;
  name: string;
  code: string;
  description: string;
  base_price: string;
  duration_minutes: number;
  specialty_id: string | null;
  specialty_name: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
}

export class ServiceApiError extends Error {
  constructor(message: string, readonly status: number,
    readonly fields: Partial<Record<keyof ServiceInput, string>> = {}, readonly invalidPage = false) {
    super(message);
  }
}
