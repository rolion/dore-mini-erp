import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { ProformaDecisionsComponent } from '../../../shared/components/proforma-decisions/proforma-decisions.component';
import { DecisionLineView } from '../../../shared/models/proforma-decisions';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import { Proforma, ProformaFailure, STATUS_CLASSES, statusLabel } from '../models/proforma';
import { ProformasApiService } from '../services/proformas-api.service';

/** Detalle de proforma con versiones y acciones según `allowed_actions` del servidor. */
@Component({
  selector: 'app-proforma-detail',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe, ProformaDecisionsComponent],
  templateUrl: './proforma-detail.component.html',
  styleUrl: './proforma-detail.component.scss',
})
export class ProformaDetailComponent implements OnInit {
  private api = inject(ProformasApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  readonly statusLabel = statusLabel;
  readonly classes = STATUS_CLASSES;

  proforma: Proforma | null = null;
  loading = true;
  saving = false;
  error = '';
  dialogError = '';

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => this.load(params.get('id') ?? ''));
  }

  can(action: string): boolean {
    return !!this.proforma?.allowed_actions.includes(action as never);
  }

  /** Relee la proforma tras registrar o rectificar una decisión. */
  reload(): void {
    if (this.proforma) this.load(this.proforma.id);
  }

  lineViews(): DecisionLineView[] {
    return (this.proforma?.lines ?? []).map(line => ({ ...line, piece: line.piece || (line.treatment_item_id ? '—' : '') }));
  }

  private load(id: string): void {
    this.loading = true;
    this.error = '';
    this.api.get(id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false)).subscribe({
      next: proforma => this.proforma = proforma,
      error: (failure: ProformaFailure) => { this.proforma = null; this.error = failure.message; },
    });
  }

  open(dialog: HTMLDialogElement): void {
    this.dialogError = '';
    dialog.showModal();
  }

  close(dialog: HTMLDialogElement): void {
    if (!this.saving) dialog.close();
  }

  present(dialog: HTMLDialogElement): void {
    if (!this.proforma || this.saving) return;
    this.saving = true;
    this.dialogError = '';
    this.api.present(this.proforma.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: proforma => { this.proforma = proforma; dialog.close(); },
        error: (failure: ProformaFailure) => this.dialogError = failure.fields['lines'] || failure.message,
      });
  }

  newVersion(): void {
    if (!this.proforma || this.saving) return;
    this.saving = true;
    this.error = '';
    this.api.newVersion(this.proforma.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: draft => void this.router.navigate(['/pocketbiz/quotations/proformas', draft.id, 'editar']),
        error: (failure: ProformaFailure) => this.error = failure.message,
      });
  }
}
