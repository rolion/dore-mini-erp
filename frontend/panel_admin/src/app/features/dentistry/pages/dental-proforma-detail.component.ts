import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { ProformaDecisionsComponent } from '../../../shared/components/proforma-decisions/proforma-decisions.component';
import { DecisionLineView } from '../../../shared/models/proforma-decisions';
import { MoneyPipe } from '../../../shared/pipes/money.pipe';
import {
  DentalProforma, DentalProformaFailure, PROFORMA_STATUS_CLASSES, proformaStatusLabel,
} from '../models/dental-proforma';
import { DentalProformasApiService } from '../services/dental-proformas-api.service';

/** Detalle de proforma odontológica con versiones y acciones según `allowed_actions` del servidor. */
@Component({
  selector: 'app-dental-proforma-detail',
  imports: [RouterLink, MoneyPipe, DatePipe, TranslatePipe, ProformaDecisionsComponent],
  templateUrl: './dental-proforma-detail.component.html',
  styleUrl: './dental-proforma-detail.component.scss',
})
export class DentalProformaDetailComponent implements OnInit {
  private api = inject(DentalProformasApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  readonly statusLabel = proformaStatusLabel;
  readonly classes = PROFORMA_STATUS_CLASSES;

  proforma: DentalProforma | null = null;
  loading = true;
  saving = false;
  error = '';
  dialogError = '';

  ngOnInit(): void {
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(params => this.load(params.get('proformaId') ?? ''));
  }

  can(action: string): boolean {
    return !!this.proforma?.allowed_actions.includes(action as never);
  }

  /** Relee la proforma tras registrar o rectificar una decisión. */
  reload(): void {
    if (this.proforma) this.load(this.proforma.id);
  }

  lineViews(): DecisionLineView[] {
    return (this.proforma?.lines ?? []).map(line => ({ ...line, piece: line.dental_piece }));
  }

  private load(id: string): void {
    this.loading = true;
    this.error = '';
    this.api.get(id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.loading = false)).subscribe({
      next: proforma => this.proforma = proforma,
      error: (failure: DentalProformaFailure) => { this.proforma = null; this.error = failure.message; },
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
        error: (failure: DentalProformaFailure) => this.dialogError = failure.fields['lines'] || failure.message,
      });
  }

  newVersion(): void {
    if (!this.proforma || this.saving) return;
    this.saving = true;
    this.error = '';
    this.api.newVersion(this.proforma.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false))
      .subscribe({
        next: draft => void this.router.navigate(['/pocketbiz/dentistry/proformas', draft.id, 'editar']),
        error: (failure: DentalProformaFailure) => this.error = failure.message,
      });
  }
}
