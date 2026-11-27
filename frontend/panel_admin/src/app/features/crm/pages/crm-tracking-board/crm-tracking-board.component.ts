import { CdkDrag, CdkDragDrop, CdkDragHandle, CdkDropList, CdkDropListGroup, transferArrayItem } from '@angular/cdk/drag-drop';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbDropdownModule, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { tr } from '../../../../core/i18n/translate';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { sumMoney } from '../../../../shared/utils/decimal-sum';
import { StageNameDialogComponent } from '../../components/stage-name-dialog/stage-name-dialog.component';
import { TrackingCardDialogComponent } from '../../components/tracking-card-dialog/tracking-card-dialog.component';
import { CrmApiError, CrmBoard, CrmStage } from '../../models/board';
import { CrmContact } from '../../models/lead';
import { CRM_BOARD_PAGE_SIZE, CrmOpportunity, isOverdue, opportunityContact } from '../../models/opportunity';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';

export interface TrackingColumn {
  stage: CrmStage;
  cards: CrmOpportunity[];
  total: string;
}

/**
 * CRM › Seguimiento comercial › tablero: columnas (etapas activas, de izquierda a derecha) con sus tarjetas abiertas.
 * Agregar columna y tarjeta; archivar solo una columna vacía (con tarjetas se avisa que primero se muevan).
 */
@Component({
  selector: 'app-crm-tracking-board',
  templateUrl: './crm-tracking-board.component.html',
  // Mismo formato de columnas y tarjetas que Oportunidades (DDR v2); el estilo propio solo añade el menú de columna.
  styleUrls: ['../crm-opportunity-board/crm-opportunity-board.component.scss', './crm-tracking-board.component.scss'],
  imports: [TranslatePipe, RouterLink, NgbDropdownModule, DatePipe, MoneyPipe, CdkDropListGroup, CdkDropList, CdkDrag, CdkDragHandle],
})
export class CrmTrackingBoardComponent implements OnInit {
  board: CrmBoard | null = null;
  columns: TrackingColumn[] = [];
  loading = true;
  loadError = '';
  notFound = false;
  /** Aviso de una regla de negocio (409) o error de una acción; el tablero ya se recargó. */
  notice = '';
  /** Columna vacía a la espera de confirmar su archivo. */
  archiving: CrmStage | null = null;
  working = false;
  /** Tarjeta que se está moviendo (bloquea otros arrastres hasta recargar). */
  movingId: string | null = null;

  private route = inject(ActivatedRoute);
  private boardsApi = inject(CrmBoardsApiService);
  private opportunitiesApi = inject(CrmOpportunitiesApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  get boardId(): string {
    return this.route.snapshot.paramMap.get('boardId') ?? '';
  }

  load(): void {
    this.loading = true;
    this.loadError = '';
    this.notFound = false;
    this.boardsApi.list(true).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (boards) => {
        const board = boards.find((b) => b.id === this.boardId) ?? null;
        this.board = board;
        if (!board) {
          this.notFound = true;
          this.columns = [];
          this.loading = false;
          return;
        }
        this.loadCards(board);
      },
      error: (err: CrmApiError) => this.fail(err),
    });
  }

  private loadCards(board: CrmBoard): void {
    this.opportunitiesApi.list({ boardId: board.id, status: 'open', pageSize: CRM_BOARD_PAGE_SIZE })
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: (page) => {
          this.columns = this.group(board, page.results);
          this.loading = false;
        },
        error: (err: CrmApiError) => this.fail(err),
      });
  }

  private fail(err: CrmApiError): void {
    this.loadError = err.message;
    this.loading = false;
  }

  private group(board: CrmBoard, cards: CrmOpportunity[]): TrackingColumn[] {
    return [...board.stages]
      .filter((s) => s.isActive)
      .sort((a, b) => a.position - b.position)
            .map((stage) => {
        const own = cards.filter((c) => c.stageId === stage.id);
        return { stage, cards: own, total: sumMoney(own.map((c) => c.amount)) };
      });
  }

  /** Recarga tablero y tarjetas tras una acción, conservando el aviso mostrado. */
  private refresh(): void {
    this.boardsApi.list(true).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (boards) => {
        const board = boards.find((b) => b.id === this.boardId) ?? null;
        this.board = board;
        if (board) {
          this.loadCards(board);
        } else {
          this.notFound = true;
          this.columns = [];
        }
      },
      error: (err: CrmApiError) => this.fail(err),
    });
  }

  contact(card: CrmOpportunity): CrmContact | null {
    return opportunityContact(card);
  }

  overdue(card: CrmOpportunity): boolean {
    return isOverdue(card);
  }

  /** Arrastrar una tarjeta a otra columna la mueve de etapa; el tablero se recarga desde el servidor. */
  drop(event: CdkDragDrop<TrackingColumn, TrackingColumn, CrmOpportunity>): void {
    const target = event.container.data;
    const source = event.previousContainer.data;
    const card = event.item.data;
    if (event.previousContainer === event.container || this.movingId) return;
    transferArrayItem(source.cards, target.cards, event.previousIndex, event.currentIndex);
    this.movingId = card.id;
    this.notice = '';
    this.opportunitiesApi.move(card.id, target.stage.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.movingId = null;
        this.refresh();
      },
      error: (err: CrmApiError) => {
        this.movingId = null;
        this.notice = err.fieldErrors['stageId'] ?? err.message;
        this.refresh();
      },
    });
  }

  addColumn(): void {
    if (!this.board) return;
    this.notice = '';
    const ref = this.modal.open(StageNameDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as StageNameDialogComponent).boardId = this.board.id;
    ref.result.then(() => this.refresh(), () => undefined);
  }

  addCard(column: TrackingColumn): void {
    if (!this.board) return;
    this.notice = '';
    const ref = this.modal.open(TrackingCardDialogComponent, { centered: true, backdrop: 'static', size: 'lg' });
    (ref.componentInstance as TrackingCardDialogComponent).open({ boardId: this.board.id, stageId: column.stage.id });
    ref.result.then(() => this.refresh(), () => undefined);
  }

  /** Archivar: con tarjetas activas se bloquea con aviso; vacía, pide confirmación. */
  requestArchive(column: TrackingColumn): void {
    this.archiving = null;
    if (column.cards.length) {
      this.notice = tr('CRM.TRACKING.ARCHIVAR_BLOQUEADO', { name: column.stage.name, n: column.cards.length });
      return;
    }
    this.notice = '';
    this.archiving = column.stage;
  }

  cancelArchive(): void {
    this.archiving = null;
  }

  confirmArchive(): void {
    const stage = this.archiving;
    if (!stage || !this.board || this.working) return;
    this.working = true;
    this.boardsApi.archiveStage(this.board.id, stage.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.working = false;
        this.archiving = null;
        this.refresh();
      },
      error: (err: CrmApiError) => {
        this.working = false;
        this.archiving = null;
        // 409 `stage_has_cards`: alguien agregó tarjetas entretanto; se avisa y se recarga el tablero.
        this.notice = err.code === 'stage_has_cards'
          ? tr('CRM.TRACKING.ARCHIVAR_BLOQUEADO', { name: stage.name, n: err.cardCount })
          : err.message;
        this.refresh();
      },
    });
  }
}
