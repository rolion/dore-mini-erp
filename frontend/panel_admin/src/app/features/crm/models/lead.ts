export const CRM_LEAD_NAME_MAX_LENGTH = 150;

/** Persona o cliente al que se refiere una oportunidad (`{id, name, phone}` en la API). */
export interface CrmContact {
  id: string;
  name: string;
  phone: string;
}

/** Prospecto tal como lo entrega `GET /api/crm/leads/`. */
export interface CrmLeadDto {
  id: string;
  name: string;
  phone: string;
  normalized_phone: string;
  email: string;
  converted_customer_id: string | null;
  created_at: string;
}

export interface CrmLeadPageDto {
  count: number;
  next: string | null;
  previous: string | null;
  results: CrmLeadDto[];
}

export interface CrmLead {
  id: string;
  name: string;
  phone: string;
  normalizedPhone: string;
  email: string;
  /** Cliente al que se convirtió; `null` mientras sigue siendo prospecto. */
  convertedCustomerId: string | null;
  createdAt: string;
}

export interface CrmLeadPage {
  count: number;
  results: CrmLead[];
}

export interface CrmLeadListParams {
  search?: string;
  /** `undefined` = todos. */
  converted?: boolean;
  page?: number;
  pageSize?: number;
}

export interface CrmLeadInput {
  name: string;
  phone: string;
  email: string;
}

export interface CrmLeadConversionDto {
  lead: CrmLeadDto;
  customer: CrmContact;
  created: boolean;
}

/** Resultado de convertir un prospecto: el cliente vinculado y si se creó en esta conversión. */
export interface CrmLeadConversion {
  lead: CrmLead;
  customer: CrmContact;
  created: boolean;
}
