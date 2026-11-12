import { DatePipe } from '@angular/common';
import { Component, DestroyRef, computed, inject, input, output, signal } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import {
  ACCEPTANCE_MEDIA, ACCEPTANCE_TONES, AcceptanceStatus, DECISION_NAME_MAX, DECISION_REASON_MAX, DECISION_TONES,
  DECISION_REFERENCE_MAX, DecisionAction, DecisionBody, DecisionFailure, DecisionHistoryItem, DecisionLineView,
  ProformaTotals, acceptanceLabel, decisionLabel, lineKindLabel, mediumLabel,
} from '../../models/proforma-decisions';
import { MoneyPipe } from '../../pipes/money.pipe';
import { StatusBadgeComponent } from '../status-badge/status-badge.component';
import { ProformaApiBase, ProformaDecisionsApiService } from '../../services/proforma-decisions-api.service';
import { sumMoney } from '../../utils/decimal-sum';

/**
 * Líneas de una proforma con la decisión del paciente por tratamiento: totales propuesto/aceptado/pendiente,
 * selección, registro de decisión con resumen, rectificación e historial. Presentacional: el backend decide
 * qué acciones existen (`actions`) y valida cada regla.
 */
@Component({
  selector: 'app-proforma-decisions',
  imports: [ReactiveFormsModule, RouterLink, MoneyPipe, DatePipe, TranslatePipe, StatusBadgeComponent],
  templateUrl: './proforma-decisions.component.html',
  styleUrl: './proforma-decisions.component.scss',
})
export class ProformaDecisionsComponent {
  private api = inject(ProformaDecisionsApiService);
  private fb = inject(FormBuilder);
  private destroyRef = inject(DestroyRef);

  readonly base = input.required<ProformaApiBase>();
  readonly proformaId = input.required<string>();
  readonly status = input.required<string>();
  readonly lines = input.required<DecisionLineView[]>();
  readonly totals = input.required<ProformaTotals>();
  readonly acceptanceStatus = input.required<AcceptanceStatus>();
  readonly actions = input<DecisionAction[]>([]);
  readonly history = input<DecisionHistoryItem[]>([]);
  /** Clave de traducción del encabezado de la columna de pieza/referencia; `null` si no hay columna. */
  readonly pieceLabelKey = input<string | null>(null);
  /** Quién acepta por defecto: el responsable del paciente menor, o el propio paciente/cliente (siempre editable). */
  readonly defaultAcceptor = input<string>('');
  /** Importe cobrado y saldo (solo si el módulo Cobros está habilitado); `null` oculta esas filas. */
  readonly collection = input<{ paid: string; balance: string } | null>(null);
  /** Hay saldo por cobrar y el módulo Cobros está habilitado: tras aceptar se ofrece «Cobrar ahora». */
  readonly collectible = input<boolean>(false);
  readonly changed = output<void>();
  readonly collect = output<void>();

  readonly media = ACCEPTANCE_MEDIA;
  readonly nameMax = DECISION_NAME_MAX;
  readonly referenceMax = DECISION_REFERENCE_MAX;
  readonly reasonMax = DECISION_REASON_MAX;
  readonly decisionLabel = decisionLabel;
  readonly acceptanceLabel = acceptanceLabel;
  readonly mediumLabel = mediumLabel;
  readonly lineKindLabel = lineKindLabel;
  readonly decisionTones = DECISION_TONES;
  readonly acceptanceTones = ACCEPTANCE_TONES;

  readonly selected = signal<ReadonlySet<string>>(new Set());
  readonly mode = signal<'accepted' | 'rejected'>('accepted');
  readonly rectifyTarget = signal<DecisionLineView | null>(null);
  readonly saving = signal(false);
  readonly error = signal('');
  readonly fieldErrors = signal<Record<string, string>>({});
  readonly success = signal('');
  /** La última operación fue una aceptación: habilita el CTA «Cobrar ahora». */
  readonly justAccepted = signal(false);
  readonly historyPage = signal(1);
  readonly pageSize = 10;

  private idempotencyKey = '';

  readonly form = this.fb.nonNullable.group({
    accepted_by_name: ['', [Validators.maxLength(DECISION_NAME_MAX)]],
    medium: ['' as DecisionBody['medium']],
    reference: ['', [Validators.maxLength(DECISION_REFERENCE_MAX)]],
    reason: ['', [Validators.maxLength(DECISION_REASON_MAX)]],
  });

  readonly canDecide = computed(() => this.status() === 'presented' && this.actions().includes('decide'));
  readonly canRectify = computed(() => this.status() === 'presented' && this.actions().includes('rectify'));
  readonly pendingLines = computed(() => this.lines().filter(line => (line.decision ?? 'pending') === 'pending'));
  readonly chosen = computed(() => this.lines().filter(line => this.selected().has(line.id)));
  readonly chosenAmount = computed(() => sumMoney(this.chosen().map(line => line.subtotal)));
  readonly allPendingSelected = computed(() =>
    this.pendingLines().length > 0 && this.pendingLines().every(line => this.selected().has(line.id)));
  readonly pagedHistory = computed(() => {
    const start = (this.historyPage() - 1) * this.pageSize;
    return this.history().slice(start, start + this.pageSize);
  });
  readonly historyPages = computed(() => Math.max(1, Math.ceil(this.history().length / this.pageSize)));

  selectable(line: DecisionLineView): boolean {
    return this.canDecide() && (line.decision ?? 'pending') === 'pending';
  }

  isLocked(line: DecisionLineView): boolean {
    return this.status() === 'draft' && !!line.origin_line_id && line.decision === 'accepted';
  }

  toggle(line: DecisionLineView, checked: boolean): void {
    const next = new Set(this.selected());
    if (checked) next.add(line.id); else next.delete(line.id);
    this.selected.set(next);
  }

  toggleAll(checked: boolean): void {
    this.selected.set(checked ? new Set(this.pendingLines().map(line => line.id)) : new Set());
  }

  // --- registrar decisión --------------------------------------------------------------------------------
  openDecision(mode: 'accepted' | 'rejected', dialog: HTMLDialogElement): void {
    if (this.chosen().length === 0) return;
    this.mode.set(mode);
    this.rectifyTarget.set(null);
    this.resetDialog();
    this.justAccepted.set(false);
    dialog.showModal();
  }

  /** «Aceptar todo»: elige todas las líneas sin decidir y abre el diálogo de aceptación. */
  acceptAll(dialog: HTMLDialogElement): void {
    this.selected.set(new Set(this.pendingLines().map(line => line.id)));
    this.openDecision('accepted', dialog);
  }

  /** Valida los datos de la decisión; devuelve `true` si se puede confirmar. */
  private validDecision(): boolean {
    this.fieldErrors.set({});
    const value = this.form.getRawValue();
    const errors: Record<string, string> = {};
    if (this.mode() === 'accepted' && !value.accepted_by_name.trim()) errors['accepted_by_name'] = 'PROFORMA_DECISIONS.E_ACCEPTED_BY_NAME';
    if (this.mode() === 'accepted' && !value.medium) errors['medium'] = 'PROFORMA_DECISIONS.E_MEDIUM';
    if (this.form.invalid) errors['form'] = 'PROFORMA_DECISIONS.ERR_REVISA';
    this.fieldErrors.set(errors);
    return Object.keys(errors).length === 0;
  }

  readonly titleKey = computed(() => this.rectifyTarget() ? 'PROFORMA_DECISIONS.DLG_RECTIFICAR'
    : this.mode() === 'accepted' ? 'PROFORMA_DECISIONS.DLG_ACEPTAR' : 'PROFORMA_DECISIONS.DLG_RECHAZAR');

  submit(dialog: HTMLDialogElement): void {
    if (this.rectifyTarget()) this.confirmRectify(dialog);
    else if (this.validDecision()) this.confirm(dialog);
  }

  confirm(dialog: HTMLDialogElement): void {
    if (this.saving() || this.chosen().length === 0) return;
    const body = this.body(this.mode(), this.chosen().map(line => line.id));
    this.run(this.api.decide(this.base(), this.proformaId(), body), dialog, 'PROFORMA_DECISIONS.OK_DECISION');
  }

  // --- rectificar ----------------------------------------------------------------------------------------
  openRectify(line: DecisionLineView, dialog: HTMLDialogElement): void {
    this.rectifyTarget.set(line);
    this.mode.set(line.decision === 'accepted' ? 'rejected' : 'accepted');
    this.resetDialog();
    dialog.showModal();
  }

  confirmRectify(dialog: HTMLDialogElement): void {
    const target = this.rectifyTarget();
    if (!target || this.saving()) return;
    const value = this.form.getRawValue();
    const errors: Record<string, string> = {};
    if (!value.reason.trim()) errors['reason'] = 'PROFORMA_DECISIONS.E_REASON_OBLIGATORIO';
    if (this.mode() === 'accepted' && !value.accepted_by_name.trim()) errors['accepted_by_name'] = 'PROFORMA_DECISIONS.E_ACCEPTED_BY_NAME';
    if (this.mode() === 'accepted' && !value.medium) errors['medium'] = 'PROFORMA_DECISIONS.E_MEDIUM';
    this.fieldErrors.set(errors);
    if (Object.keys(errors).length > 0 || this.form.invalid) return;
    this.run(this.api.rectify(this.base(), this.proformaId(), target.id, this.body(this.mode(), undefined)), dialog,
      'PROFORMA_DECISIONS.OK_RECTIFICACION');
  }

  close(dialog: HTMLDialogElement): void {
    if (!this.saving()) dialog.close();
  }

  setPage(page: number): void {
    this.historyPage.set(Math.min(Math.max(1, page), this.historyPages()));
  }

  private body(decision: 'accepted' | 'rejected', lineIds: string[] | undefined): DecisionBody {
    const value = this.form.getRawValue();
    return {
      idempotency_key: this.idempotencyKey, decision, ...(lineIds ? { line_ids: lineIds } : {}),
      accepted_by_name: value.accepted_by_name.trim(), medium: value.medium,
      reference: value.reference.trim(), reason: value.reason.trim(),
    };
  }

  private resetDialog(): void {
    this.form.reset({ accepted_by_name: this.defaultAcceptor(), medium: '', reference: '', reason: '' });
    this.fieldErrors.set({});
    this.error.set('');
    this.idempotencyKey = crypto.randomUUID(); // se reutiliza en cada reintento de esta confirmación
  }

  private run(call: ReturnType<ProformaDecisionsApiService['decide']>, dialog: HTMLDialogElement, successKey: string): void {
    this.saving.set(true);
    this.error.set('');
    call.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving.set(false))).subscribe({
      next: () => {
        dialog.close();
        this.selected.set(new Set());
        this.success.set(successKey);
        this.justAccepted.set(this.mode() === 'accepted' && !this.rectifyTarget());
        this.changed.emit();
      },
      error: (failure: DecisionFailure) => {
        this.error.set(failure.message);
        this.fieldErrors.set(failure.fields);
      },
    });
  }
}
