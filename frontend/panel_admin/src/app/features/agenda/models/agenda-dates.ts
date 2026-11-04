import { RepeatMode } from './agenda';

/** Fecha ISO (YYYY-MM-DD) desplazada `offset` días; opera en UTC para no depender de la zona del navegador. */
export function shiftDate(value: string, offset: number): string {
  const date = new Date(`${value.slice(0, 10)}T00:00:00Z`);
  date.setUTCDate(date.getUTCDate() + offset);
  return date.toISOString().slice(0, 10);
}

/** Última fecha de vigencia para «solo esta semana» y «hasta fin de mes», a partir del lunes visible. */
export function repeatUntil(mode: Exclude<RepeatMode, 'custom'>, monday: string): string {
  const sunday = shiftDate(monday, 6);
  if (mode === 'week') return sunday;
  const [year, month] = monday.split('-').map(Number);
  const monthEnd = new Date(Date.UTC(year, month, 0)).toISOString().slice(0, 10);
  return monthEnd > sunday ? monthEnd : sunday;
}

/** Ausencia de «todo el día»: el servidor guarda el fin como el inicio del día siguiente. */
export function fullDayRange(from: string, to: string): { starts: string; ends: string } {
  return { starts: `${from}T00:00`, ends: `${shiftDate(to, 1)}T00:00` };
}

/** Si la ausencia cubre días completos devuelve sus fechas inclusivas; si no, null. */
export function asFullDays(starts: string, ends: string): { from: string; to: string } | null {
  const whole = (value: string) => value.slice(11, 16) === '00:00';
  if (!whole(starts) || !whole(ends) || ends.slice(0, 10) <= starts.slice(0, 10)) return null;
  return { from: starts.slice(0, 10), to: shiftDate(ends, -1) };
}

/** Minutos entre dos valores `YYYY-MM-DDTHH:mm` (hora civil, sin zona). */
export function minutesBetween(starts: string, ends: string): number {
  const parse = (value: string) => Date.parse(`${value.slice(0, 16)}:00Z`);
  return Math.round((parse(ends) - parse(starts)) / 60000);
}
