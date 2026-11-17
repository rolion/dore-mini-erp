import { Component, DestroyRef, ElementRef, ViewChild, inject, input, output } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { CommitmentLine, ReceivableFailure, ServiceRendered, SourceKind, localToday } from '../../models/receivable';
import { MoneyPipe } from '../../pipes/money.pipe';
import { ReceivablesApiService } from '../../services/receivables-api.service';
import { PostingIssuesAlertComponent } from '../posting-issues-alert/posting-issues-alert.component';

/**
 * Confirmación de «Marcar como prestado» de un tratamiento aceptado: muestra el importe, pide la fecha de prestación
 * (no futura) y advierte que no se puede deshacer. Presentacional: el servidor valida estado, fecha, cobertura y
 * configuración contable, y es idempotente por tratamiento.
 */
@Component({
  selector: 'app-service-dialog',
  imports: [ReactiveFormsModule, MoneyPipe, TranslatePipe, PostingIssuesAlertComponent],
  templateUrl: './service-dialog.component.html',
  styleUrl: './service-dialog.component.scss',
})
export class ServiceDialogComponent {
  private api = inject(ReceivablesApiService);
  private fb = inject(FormBuilder).nonNullable;
  private destroyRef = inject(DestroyRef);

  readonly kind = input.required<SourceKind>();
  readonly number = input.required<string>();
  /** Se emite tras marcar el tratamiento (el padre refresca y anuncia el resultado). */
  readonly rendered = output<ServiceRendered>();

  @ViewChild('dlg', { static: true }) private dialog!: ElementRef<HTMLDialogElement>;

  readonly today = localToday();
  line: CommitmentLine | null = null;
  saving = false;
  failure: ReceivableFailure | null = null;
  private opener: HTMLElement | null = null;

  readonly form = this.fb.group({ service_date: [this.today, [Validators.required]] });

  get canConfirm(): boolean {
    return !this.saving && !!this.line && this.form.valid;
  }

  open(line: CommitmentLine, opener?: HTMLElement | null): void {
    this.opener = opener ?? (document.activeElement as HTMLElement | null);
    this.line = line;
    this.failure = null;
    this.form.reset({ service_date: localToday() });
    this.dialog.nativeElement.showModal();
  }

  confirm(): void {
    if (!this.canConfirm || !this.line) return;
    this.saving = true;
    this.failure = null;
    this.api
      .renderService(this.kind(), this.number(), {
        line_id: this.line.line_id,
        service_date: this.form.controls.service_date.value || null,
      })
      .pipe(takeUntilDestroyed(this.destroyRef), finalize(() => (this.saving = false)))
      .subscribe({
        next: (result) => {
          this.dismiss(true); // `saving` sigue en true hasta `finalize`: se cierra sin pasar por `close()`
          this.rendered.emit(result);
        },
        error: (failure: ReceivableFailure) => (this.failure = failure),
      });
  }

  /** Cancelar o seguir un enlace: no se puede cerrar mientras se guarda. */
  close(): void {
    if (!this.saving) this.dismiss();
  }

  /** Tras marcar el tratamiento el botón desaparece: el foco lo lleva el padre al aviso de resultado, al recargar. */
  private dismiss(afterService = false): void {
    this.dialog.nativeElement.close();
    if (!afterService) this.opener?.focus();
  }
}
