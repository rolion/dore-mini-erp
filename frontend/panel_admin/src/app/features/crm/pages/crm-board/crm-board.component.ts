import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, distinctUntilChanged } from 'rxjs';
import { ArchiveStageDialogComponent } from '../../components/archive-stage-dialog/archive-stage-dialog.component';
import { BoardNameDialogComponent } from '../../components/board-name-dialog/board-name-dialog.component';
import { CRM_NAME_MAX_LENGTH, CrmApiError, CrmBoard, CrmStage } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** CRM › Tablero: selector de tablero y editor de etapas (crear, renombrar, ordenar y archivar). */
@Component({
  selector: 'app-crm-board',
  templateUrl: './crm-board.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink],
})
export class CrmBoardComponent implements OnInit {
  readonly nameMaxLength = CRM_NAME_MAX_LENGTH;
  readonly boardSelect = inject(FormBuilder).nonNullable.control('');
  readonly newStage = inject(FormBuilder).nonNullable.control('', [notBlank, Validators.maxLength(CRM_NAME_MAX_LENGTH)]);
  readonly editName = inject(FormBuilder).nonNullable.control('', [notBlank, Validators.maxLength(CRM_NAME_MAX_LENGTH)]);

  boards: CrmBoard[] = [];
  showArchived = false;
  loading = true;
  saving = false;
  loadError = '';
  /** Aviso de una regla de negocio (409) o de un error al guardar; la lista se recarga con el estado real. */
  notice = '';
  stageError = '';
  editingStageId: string | null = null;

  private api = inject(CrmBoardsApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.boardSelect.valueChanges.pipe(distinctUntilChanged(), takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.cancelEdit();
      this.notice = '';
    });
    this.newStage.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.stageError = ''));
    this.load();
  }

  get visibleBoards(): CrmBoard[] {
    return this.boards.filter((b) => b.isActive || this.showArchived);
  }

  get selected(): CrmBoard | null {
    return this.boards.find((b) => b.id === this.boardSelect.value) ?? null;
  }

  load(selectId?: string): void {
    this.loading = true;
    this.loadError = '';
    this.api.list().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (boards) => {
        this.boards = boards;
        this.loading = false;
        this.pick(selectId ?? this.boardSelect.value);
      },
      error: (err: CrmApiError) => {
        this.loading = false;
        this.loadError = err.message;
      },
    });
  }

  toggleArchived(): void {
    this.showArchived = !this.showArchived;
    this.pick(this.boardSelect.value);
  }

  /** Mantiene el tablero elegido si sigue visible; si no, el primero visible (o ninguno). */
  private pick(id: string): void {
    const visible = this.visibleBoards;
    this.boardSelect.setValue(visible.some((b) => b.id === id) ? id : (visible[0]?.id ?? ''));
    if (visible.length) {
      this.boardSelect.enable({ emitEvent: false });
    } else {
      this.boardSelect.disable({ emitEvent: false });
    }
  }

  /** Reemplaza el tablero por el estado que devolvió el servidor (la fuente de verdad). */
  private apply(board: CrmBoard): void {
    const exists = this.boards.some((b) => b.id === board.id);
    this.boards = exists ? this.boards.map((b) => (b.id === board.id ? board : b)) : [...this.boards, board];
    this.pick(board.id);
  }

  private run(request: Observable<CrmBoard>, onDone?: () => void): void {
    if (this.saving) {
      return;
    }
    this.saving = true;
    this.notice = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (board) => {
        this.saving = false;
        this.apply(board);
        onDone?.();
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.stageError = err.fieldErrors.name ?? '';
        this.notice = this.stageError ? '' : err.message;
        if (err.status === 409 || err.status === 404) {
          this.load(this.boardSelect.value); // el estado cambió en otro lado: recarga
        }
      },
    });
  }

  // --- tableros ---
  createBoard(): void {
    const ref = this.modal.open(BoardNameDialogComponent, { centered: true });
    ref.result.then((board: CrmBoard) => this.apply(board), () => undefined);
  }

  renameBoard(): void {
    const board = this.selected;
    if (!board) {
      return;
    }
    const ref = this.modal.open(BoardNameDialogComponent, { centered: true });
    (ref.componentInstance as BoardNameDialogComponent).edit(board);
    ref.result.then((saved: CrmBoard) => this.apply(saved), () => undefined);
  }

  archiveBoard(): void {
    const board = this.selected;
    if (board) {
      this.run(this.api.archive(board.id));
    }
  }

  reactivateBoard(): void {
    const board = this.selected;
    if (board) {
      this.run(this.api.reactivate(board.id));
    }
  }

  // --- etapas ---
  addStage(): void {
    const board = this.selected;
    if (!board || this.newStage.invalid) {
      this.newStage.markAsTouched();
      return;
    }
    this.run(this.api.addStage(board.id, this.newStage.value.trim()), () => this.newStage.reset(''));
  }

  startEdit(stage: CrmStage): void {
    this.editingStageId = stage.id;
    this.editName.setValue(stage.name);
    this.stageError = '';
  }

  cancelEdit(): void {
    this.editingStageId = null;
    this.stageError = '';
  }

  saveEdit(stage: CrmStage): void {
    const board = this.selected;
    if (!board || this.editName.invalid) {
      this.editName.markAsTouched();
      return;
    }
    this.run(this.api.renameStage(board.id, stage.id, this.editName.value.trim()), () => this.cancelEdit());
  }

  move(stage: CrmStage, direction: -1 | 1): void {
    const board = this.selected;
    if (!board) {
      return;
    }
    const ids = board.stages.map((s) => s.id);
    const from = ids.indexOf(stage.id);
    const to = from + direction;
    if (from < 0 || to < 0 || to >= ids.length) {
      return;
    }
    [ids[from], ids[to]] = [ids[to], ids[from]];
    this.run(this.api.reorderStages(board.id, ids));
  }

  archiveStage(stage: CrmStage): void {
    const board = this.selected;
    if (!board) {
      return;
    }
    const ref = this.modal.open(ArchiveStageDialogComponent, { centered: true });
    (ref.componentInstance as ArchiveStageDialogComponent).open(board, stage);
    ref.result.then((saved: CrmBoard) => this.apply(saved), () => undefined);
  }
}
