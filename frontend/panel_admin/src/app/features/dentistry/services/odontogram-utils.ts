import { tr } from '../../../core/i18n/translate';
import { Dentition, Finding, OdontogramCatalog, OdontogramCondition, PieceKind, SurfaceCode } from '../models/odontogram';

/** Ayudas de la interfaz para la nomenclatura FDI (INV-01…INV-03); el backend es la autoridad. */

export function quadrant(piece: number): number { return Math.floor(piece / 10); }
export function position(piece: number): number { return piece % 10; }
export function isTemporaryPiece(piece: number): boolean { return quadrant(piece) >= 5; }
export function isUpperPiece(piece: number): boolean { return [1, 2, 5, 6].includes(quadrant(piece)); }
/** Los cuadrantes 1, 4, 5 y 8 están a la derecha del paciente (a la izquierda del gráfico). */
export function isRightSide(piece: number): boolean { return [1, 4, 5, 8].includes(quadrant(piece)); }

export function isValidPiece(piece: number, dentition: Dentition, teeth: OdontogramCatalog['teeth']): boolean {
  const permanent = teeth.permanent.includes(piece);
  const temporary = teeth.temporary.includes(piece);
  if (dentition === 'permanent') return permanent;
  if (dentition === 'temporary') return temporary;
  return permanent || temporary;
}

export function pieceKind(piece: number): PieceKind {
  const pos = position(piece);
  if (pos === 1 || pos === 2) return 'incisor';
  if (pos === 3) return 'canine';
  if (isTemporaryPiece(piece)) return 'molar';
  return pos <= 5 ? 'premolar' : 'molar';
}

export function isAnterior(piece: number): boolean {
  const kind = pieceKind(piece);
  return kind === 'incisor' || kind === 'canine';
}

/** Superficies válidas por pieza: anteriores M, D, V, I y P/L; posteriores M, D, V, O y P/L. */
export function validSurfaces(piece: number): SurfaceCode[] {
  return ['M', 'D', 'V', isAnterior(piece) ? 'I' : 'O', isUpperPiece(piece) ? 'P' : 'L'];
}

export interface ArchRow { id: string; upper: boolean; temporary: boolean; pieces: number[]; }

function sorted(teeth: number[], quadrants: number[], descending: boolean): number[] {
  const side = teeth.filter(piece => quadrants.includes(quadrant(piece)));
  return side.sort((a, b) => descending ? b - a : a - b);
}

/** Filas del gráfico según la dentición: la mixta muestra permanentes y temporales de cada arcada. */
export function archRows(dentition: Dentition, teeth: OdontogramCatalog['teeth']): ArchRow[] {
  const row = (id: string, upper: boolean, temporary: boolean): ArchRow => {
    const source = temporary ? teeth.temporary : teeth.permanent;
    const [right, left] = temporary ? (upper ? [5, 6] : [8, 7]) : (upper ? [1, 2] : [4, 3]);
    return { id, upper, temporary, pieces: [...sorted(source, [right], true), ...sorted(source, [left], false)] };
  };
  if (dentition === 'permanent') return [row('upper-permanent', true, false), row('lower-permanent', false, false)];
  if (dentition === 'temporary') return [row('upper-temporary', true, true), row('lower-temporary', false, true)];
  return [row('upper-permanent', true, false), row('upper-temporary', true, true),
    row('lower-temporary', false, true), row('lower-permanent', false, false)];
}

export function findingsOf(findings: Finding[], piece: number): Finding[] {
  return findings.filter(finding => finding.piece === piece);
}

export function conditionOf(catalog: OdontogramCatalog | null, code: string): OdontogramCondition | undefined {
  return catalog?.conditions.find(condition => condition.code === code);
}

/** Nombre visible de la condición: usa el catálogo de idiomas y cae al nombre del servidor si no hay clave. */
export function conditionName(catalog: OdontogramCatalog | null, code: string): string {
  const key = `DENTISTRY.ODONTOGRAM.CONDITION_${code.toUpperCase()}`;
  const text = tr(key);
  return text !== key ? text : (conditionOf(catalog, code)?.name ?? code);
}

export function surfaceName(catalog: OdontogramCatalog | null, code: SurfaceCode): string {
  const key = `DENTISTRY.ODONTOGRAM.SURFACE_${code}`;
  const text = tr(key);
  return text !== key ? text : (catalog?.surfaces.find(surface => surface.code === code)?.name ?? code);
}

export function pieceKindName(piece: number): string {
  return tr(`DENTISTRY.ODONTOGRAM.KIND_${pieceKind(piece).toUpperCase()}`);
}

export function pieceDentitionName(piece: number): string {
  return tr(isTemporaryPiece(piece) ? 'DENTISTRY.ODONTOGRAM.DENT_TEMPORARY' : 'DENTISTRY.ODONTOGRAM.DENT_PERMANENT');
}

/** Texto de un hallazgo: «Caries (O, M)» o «Corona». */
export function findingLabel(catalog: OdontogramCatalog | null, finding: Finding): string {
  const name = conditionName(catalog, finding.condition);
  return finding.surfaces.length ? `${name} (${finding.surfaces.join(', ')})` : name;
}

/** Texto accesible de una pieza: «Pieza 16, molar permanente, Caries (O)» o «…, sin evaluar». */
export function pieceAriaLabel(catalog: OdontogramCatalog | null, piece: number, findings: Finding[]): string {
  const own = findingsOf(findings, piece);
  const summary = own.length ? own.map(finding => findingLabel(catalog, finding)).join('; ')
    : tr('DENTISTRY.ODONTOGRAM.SIN_EVALUAR');
  return tr('DENTISTRY.ODONTOGRAM.PIEZA_ARIA', {
    piece, type: pieceKindName(piece).toLowerCase(), dent: pieceDentitionName(piece).toLowerCase(), summary,
  });
}

/** Aplana los errores de validación del servidor (objetos y listas anidados) a una lista de textos. */
export function flattenErrors(body: unknown, prefix = ''): string[] {
  if (body === null || body === undefined) return [];
  if (typeof body === 'string') return [prefix ? `${prefix}: ${body}` : body];
  if (Array.isArray(body)) return body.flatMap(item => flattenErrors(item, prefix));
  if (typeof body === 'object') {
    return Object.entries(body as Record<string, unknown>).flatMap(([key, value]) =>
      flattenErrors(value, /^\d+$/.test(key) ? prefix : key));
  }
  return [];
}
