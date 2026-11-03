export type ProfileKind = 'professionals' | 'specialties';

export interface SpecialtyOption { id: string; name: string; active: boolean; }
export interface UserOption { id: number; name: string; }
export interface Profile extends SpecialtyOption {
  identification?: string;
  phone?: string;
  email?: string;
  registration_number?: string;
  user_id?: number | null;
  specialty_ids?: string[];
  specialties?: SpecialtyOption[];
  created_by: number;
  updated_by: number;
  created_at: string;
  updated_at: string;
}
export interface ProfileInput {
  name: string;
  identification?: string;
  phone?: string;
  email?: string;
  registration_number?: string;
  user_id?: number | null;
  specialty_ids?: string[];
}
