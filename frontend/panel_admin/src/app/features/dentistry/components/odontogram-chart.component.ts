import { Component, ElementRef, computed, inject, input, output, signal } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { tr } from '../../../core/i18n/translate';
import { Dentition, Finding, OdontogramCatalog } from '../models/odontogram';
import {
  ArchRow, archRows, conditionName, conditionOf, findingsOf, isAnterior, isRightSide, isTemporaryPiece, isUpperPiece,
  pieceAriaLabel,
} from '../services/odontogram-utils';

interface SurfaceShape { code: string; points: string; color: string | null; }

interface ToothView {
  piece: number;
  label: string;
  abbr: string;
  evaluated: boolean;
  temporary: boolean;
  wholeColor: string | null;
  selected: boolean;
  shapes: SurfaceShape[];
}

interface RowView { row: ArchRow; teeth: ToothView[]; }

/** Odontograma gráfico (SVG propio): cada pieza FDI es un botón con su abreviatura; el color nunca va solo. */
@Component({
  selector: 'app-odontogram-chart',
  imports: [TranslatePipe],
  templateUrl: './odontogram-chart.component.html',
  styleUrl: './odontogram-chart.component.scss',
})
export class OdontogramChartComponent {
  readonly dentition = input.required<Dentition>();
  readonly catalog = input.required<OdontogramCatalog>();
  readonly findings = input.required<Finding[]>();
  readonly selected = input<number | null>(null);
  readonly pieceSelected = output<number>();

  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private focusable = signal<number | null>(null);

  readonly rows = computed<RowView[]>(() => archRows(this.dentition(), this.catalog().teeth).map(row => ({
    row, teeth: row.pieces.map(piece => this.tooth(piece)),
  })));

  readonly legend = computed(() => this.catalog().conditions.map(condition => ({
    code: condition.code, abbr: condition.abbr, color: condition.color, name: conditionName(this.catalog(), condition.code),
  })));

  get mixed(): boolean { return this.dentition() === 'mixed'; }

  tabIndex(piece: number): number {
    const first = this.rows()[0]?.teeth[0]?.piece ?? null;
    const target = this.selected() ?? this.focusable() ?? first;
    return target === piece ? 0 : -1;
  }

  get temporaryMark(): string { return tr('DENTISTRY.ODONTOGRAM.SIGLA_TEMPORAL'); }
  get permanentMark(): string { return tr('DENTISTRY.ODONTOGRAM.SIGLA_PERMANENTE'); }

  rowLabel(row: ArchRow): string {
    const arch = tr(row.upper ? 'DENTISTRY.ODONTOGRAM.ARCADA_SUPERIOR' : 'DENTISTRY.ODONTOGRAM.ARCADA_INFERIOR');
    return this.mixed ? `${arch} · ${tr(row.temporary ? 'DENTISTRY.ODONTOGRAM.DENT_TEMPORARY' : 'DENTISTRY.ODONTOGRAM.DENT_PERMANENT')}` : arch;
  }

  onFocus(piece: number): void { this.focusable.set(piece); }

  onKey(event: KeyboardEvent, rowIndex: number, colIndex: number): void {
    const rows = this.rows();
    let target: number | null = null;
    const rowPieces = rows[rowIndex].teeth;
    switch (event.key) {
      case 'ArrowLeft': target = rowPieces[Math.max(0, colIndex - 1)].piece; break;
      case 'ArrowRight': target = rowPieces[Math.min(rowPieces.length - 1, colIndex + 1)].piece; break;
      case 'Home': target = rowPieces[0].piece; break;
      case 'End': target = rowPieces[rowPieces.length - 1].piece; break;
      case 'ArrowUp':
      case 'ArrowDown': {
        const next = rows[rowIndex + (event.key === 'ArrowUp' ? -1 : 1)];
        if (next) target = next.teeth[Math.min(colIndex, next.teeth.length - 1)].piece;
        break;
      }
      default: return;
    }
    event.preventDefault();
    if (target !== null) {
      this.focusable.set(target);
      this.host.nativeElement.querySelector<HTMLElement>(`[data-piece="${target}"]`)?.focus();
    }
  }

  private tooth(piece: number): ToothView {
    const own = findingsOf(this.findings(), piece);
    const catalog = this.catalog();
    const colorOf = (finding: Finding): string => conditionOf(catalog, finding.condition)?.color ?? 'secondary';
    const surfaceColor = (code: string): string | null => {
      const match = [...own].reverse().find(finding => (finding.surfaces as string[]).includes(code));
      return match ? colorOf(match) : null;
    };
    const whole = own.find(finding => finding.surfaces.length === 0);
    const right = isRightSide(piece);
    const shapes: SurfaceShape[] = [
      { code: 'V', points: '4,4 36,4 28,12 12,12', color: surfaceColor('V') },
      { code: isUpperPiece(piece) ? 'P' : 'L', points: '12,28 28,28 36,36 4,36',
        color: surfaceColor(isUpperPiece(piece) ? 'P' : 'L') },
      { code: right ? 'D' : 'M', points: '4,4 12,12 12,28 4,36', color: surfaceColor(right ? 'D' : 'M') },
      { code: right ? 'M' : 'D', points: '36,4 28,12 28,28 36,36', color: surfaceColor(right ? 'M' : 'D') },
      { code: isAnterior(piece) ? 'I' : 'O', points: '12,12 28,12 28,28 12,28',
        color: surfaceColor(isAnterior(piece) ? 'I' : 'O') },
    ];
    const first = own[0];
    const abbr = first ? (conditionOf(catalog, first.condition)?.abbr ?? first.condition) + (own.length > 1 ? '+' : '') : '';
    return {
      piece, label: pieceAriaLabel(catalog, piece, this.findings()), abbr, evaluated: own.length > 0,
      temporary: isTemporaryPiece(piece), wholeColor: whole ? colorOf(whole) : null,
      selected: this.selected() === piece, shapes,
    };
  }
}
