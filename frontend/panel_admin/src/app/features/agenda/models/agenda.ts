export interface Interval { starts: string; ends: string }

export interface Shift extends Interval {
  id: number;
  day: number;
  valid_from: string;
  valid_until: string;
  breaks: Interval[];
}

export interface Absence extends Interval { id: number; reason: string }

export interface Week {
  timezone: string;
  shifts: Shift[];
  availability: Interval[];
  absences: Absence[];
}

export interface ShiftPayload extends Interval {
  day: number;
  valid_from: string;
  valid_until: string;
  breaks: Interval[];
}

export interface MultiShiftPayload extends Interval {
  days: number[];
  valid_from: string;
  valid_until: string;
  breaks: Interval[];
}

export interface AbsencePayload extends Interval { reason: string }

export type RepeatMode = 'week' | 'month' | 'custom';
