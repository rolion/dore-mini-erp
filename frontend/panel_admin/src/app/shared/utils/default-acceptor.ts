/** Menor de edad: tiene menos de 18 años cumplidos (misma regla que `customers/domain/demographics.py`). */
export function isMinor(birthDate: string | null | undefined, today: Date = new Date()): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})/.exec(birthDate ?? '');
  if (!match) return false;
  const [year, month, day] = [Number(match[1]), Number(match[2]), Number(match[3])];
  const hadBirthday = today.getMonth() + 1 > month || (today.getMonth() + 1 === month && today.getDate() >= day);
  return today.getFullYear() - year - (hadBirthday ? 0 : 1) < 18;
}

/**
 * Quién acepta por defecto (INV-05): el responsable si el paciente es menor y tiene responsable; en otro caso el
 * propio paciente/cliente. Es solo una precarga: la persona puede cambiarla.
 */
export function defaultAcceptor(name: string, birthDate: string | null | undefined, responsibleName: string | null | undefined,
  today: Date = new Date()): string {
  const responsible = (responsibleName ?? '').trim();
  return isMinor(birthDate, today) && responsible ? responsible : name.trim();
}
