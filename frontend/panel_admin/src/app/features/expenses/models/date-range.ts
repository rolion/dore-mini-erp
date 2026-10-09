/** Fecha local en formato `AAAA-MM-DD` (sin pasar por UTC, que correría el día cerca de la medianoche). */
export function toIsoDate(date: Date): string {
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${month}-${day}`;
}

export interface DateRange {
  dateFrom: string;
  dateTo: string;
}

/** Primer y último día del mes de `today` (o del mes anterior con `monthOffset = -1`). */
export function monthRange(today: Date, monthOffset = 0): DateRange {
  const first = new Date(today.getFullYear(), today.getMonth() + monthOffset, 1);
  const last = new Date(first.getFullYear(), first.getMonth() + 1, 0);
  return { dateFrom: toIsoDate(first), dateTo: toIsoDate(last) };
}
