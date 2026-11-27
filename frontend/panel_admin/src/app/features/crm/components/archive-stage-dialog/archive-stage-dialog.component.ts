import { Component, DestroyRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { CrmApiError, CrmBoard, CrmStage } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';

/**
 * Archiva una etapa. Si tiene tarjetas exige elegir una etapa destino activa del mismo tablero; se cierra
 * devolviendo el tablero actualizado por el servidor (que reasigna y archiva en una sola transacción).
 */
@Component({
  selector: 'app-crm-archive-stage-dialog',
  templateUrl: './archive-stage-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class ArchiveStageDialogComponent {
  readonly form = inject(FormBuilder).nonNullable.group({ target: [''] });

  board!: CrmBoard;
  stage!: CrmStage;
  cardCount = 0;
  saving = false;
  errorMessage = '';
  targetError = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmBoardsApiService);
  private destroyRef = inject(DestroyRef);

  open(board: CrmBoard, stage: CrmStage): void {
    this.board = board;
    this.stage = stage;
    this.cardCount = stage.cardCount;
  }

  get targets(): CrmStage[] {
    return this.board.stages.filter((s) => s.id !== this.stage.id);
  }

  get needsTarget(): boolean {
    return this.cardCount > 0;
  }

  get canConfirm(): boolean {
    return !this.saving && (!this.needsTarget || !!this.form.controls.target.value);
  }

  confirm(): void {
    if (!this.canConfirm) {
      return;
    }
    this.saving = true;
    this.errorMessage = '';
    this.targetError = '';
    const target = this.needsTarget ? this.form.controls.target.value : undefined;
    this.api.archiveStage(this.board.id, this.stage.id, target).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (board) => {
        this.saving = false;
        this.activeModal.close(board);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        if (err.code === 'stage_has_cards') {
          // Alguien movió tarjetas a la etapa tras cargar la pantalla: pedimos el destino ahora.
          this.cardCount = err.cardCount;
        }
        this.targetError = err.fieldErrors.targetStageId ?? '';
        this.errorMessage = this.targetError ? '' : err.message;
      },
    });
  }
}
