import { AbstractControl, ValidationErrors, ValidatorFn } from '@angular/forms';

export function localDateInput(today = new Date()): string {
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, '0')}-${String(today.getDate()).padStart(2, '0')}`;
}
/** Años cumplidos a `today`; null si no hay fecha de nacimiento válida. */
export function ageAt(birth: string | null | undefined, today = new Date()): number | null {
  if (!birth) return null;
  const [year, month, day] = birth.split('-').map(Number);
  if (!year || !month || !day) return null;
  const birthdayPending = today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day);
  return today.getFullYear() - year - (birthdayPending ? 1 : 0);
}
export function minorAt(birth: string, today = new Date()): boolean {
  if (!birth) return false;
  const [year, month, day] = birth.split('-').map(Number);
  return today.getFullYear() - year - (today.getMonth() + 1 < month || (today.getMonth() + 1 === month && today.getDate() < day) ? 1 : 0) < 18;
}
export const demographicsValidator: ValidatorFn = (control: AbstractControl): ValidationErrors | null => {
  const value = control.value as { birth_date: string; responsible_name: string; responsible_phone: string };
  const errors: ValidationErrors = {};
  if (value.birth_date > localDateInput()) errors['futureBirth'] = true;
  const needsBoth = minorAt(value.birth_date) || !!value.responsible_name.trim() || !!value.responsible_phone.trim();
  if (needsBoth && !value.responsible_name.trim()) errors['responsibleName'] = true;
  if (needsBoth && !value.responsible_phone.trim()) errors['responsiblePhone'] = true;
  return Object.keys(errors).length ? errors : null;
};
