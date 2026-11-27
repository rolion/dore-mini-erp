import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { Router, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { BoardNameDialogComponent } from '../../components/board-name-dialog/board-name-dialog.component';
import { CrmApiError, CrmBoard } from '../../models/board';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';

/** CRM › Seguimiento comercial: cada tablero activo es una tarjeta que abre su tablero; «Crear nuevo tablero». */
@Component({
  selector: 'app-crm-tracking-board-list',
  templateUrl: './crm-tracking-board-list.component.html',
  styleUrl: './crm-tracking-board-list.component.scss',
  imports: [TranslatePipe, RouterLink],
})
export class CrmTrackingBoardListComponent implements OnInit {
  boards: CrmBoard[] = [];
  loading = true;
  loadError = '';

  private api = inject(CrmBoardsApiService);
  private modal = inject(NgbModal);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.loadError = '';
    this.api.list(true).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (boards) => {
        this.boards = boards;
        this.loading = false;
      },
      error: (err: CrmApiError) => {
        this.loadError = err.message;
        this.loading = false;
      },
    });
  }

  /** Abre el modal con solo el nombre; al guardar entra directo al tablero nuevo (sin columnas). */
  create(): void {
    const ref = this.modal.open(BoardNameDialogComponent, { centered: true, backdrop: 'static' });
    ref.result.then(
      (board: CrmBoard) => void this.router.navigate(['/pocketbiz/crm/tracking', board.id]),
      () => undefined,
    );
  }
}
