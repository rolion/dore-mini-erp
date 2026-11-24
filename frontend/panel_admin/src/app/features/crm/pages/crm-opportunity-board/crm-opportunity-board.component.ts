import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Subject, catchError, distinctUntilChanged, finalize, of, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { AuthService } from '../../../../core/service/auth.service';
import { ModulesService } from '../../../../core/service/modules.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { sumMoney } from '../../../../shared/utils/decimal-sum';
import {
  CLOSE_DIALOG_CONVERT, CloseOpportunityDialogComponent,
} from '../../components/close-opportunity-dialog/close-opportunity-dialog.component';
import { ConvertLeadDialogComponent } from '../../components/convert-lead-dialog/convert-lead-dialog.component';
import { OpportunityDialogComponent } from '../../components/opportunity-dialog/opportunity-dialog.component';
import { CrmApiError, CrmBoard, CrmStage } from '../../models/board';
import { CrmContact, CrmLeadConversion } from '../../models/lead';
import {
  CRM_BOARD_PAGE_SIZE, CrmOpportunity, CrmOpportunityFilters, CrmOpportunityStatus, CrmOwner, isOverdue,
  opportunityContact,
} from '../../models/opportunity';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';

export interface CrmColumn {
  stage: CrmStage;
  cards: CrmOpportunity[];
  total: string;
}

interface ContactOption {
  /** `lead:<id>` o `customer:<id>`. */
  key: string;
  name: string;
  kind: 'lead' | 'customer';
}

/**
 * CRM › Oportunidades: Kanban por etapa activa del tablero elegido, con filtros por responsable, contacto y estado.
 * Las tarjetas se mueven con «Mover a…» (sin arrastrar) y todo cambio se recarga desde el servidor.
 */
@Component({
  selector: 'app-crm-opportunity-board',
  templateUrl: './crm-opportunity-board.component.html',
  styleUrl: './crm-opportunity-board.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, MoneyPipe, DatePipe],
})
export class CrmOpportunityBoardComponent implements OnInit {
  private fb = inject(FormBuilder).nonNullable;
  readonly boardSelect = this.fb.control('');
  readonly filters = this.fb.group({
    ownerId: [''],
    contact: [''],
    status: this.fb.control<CrmOpportunityStatus>('open'),
  });

  boards: CrmBoard[] = [];
  opportunities: CrmOpportunity[] = [];
  columns: CrmColumn[] = [];
  loadingBoards = true;
  loadingCards = false;
  boardsError = '';
  cardsError = '';
  /** Aviso de una regla de negocio (409/404) tras una acción; el tablero ya se recargó. */
  notice = '';
  success = '';
  movingId: string | null = null;
  readonly salesEnabled: boolean;

  /** Responsables y contactos vistos en el tablero (sin filtros) para ofrecerlos en los filtros. */
  private knownOwners = new Map<number, CrmOwner>();
  private knownContacts = new Map<string, ContactOption>();
  private reload$ = new Subject<void>();

  private api = inject(CrmOpportunitiesApiService);
  private boardsApi = inject(CrmBoardsApiService);
  private modal = inject(NgbModal);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    this.salesEnabled = inject(ModulesService).enabledKeysValue?.has('sales') ?? false;
  }

  ngOnInit(): void {
    this.reload$.pipe(
      switchMap(() => {
        const board = this.selected;
        if (!board) {
          this.opportunities = [];
          this.columns = [];
          return of(null);
        }
        this.loadingCards = true;
        this.cardsError = '';
        return this.api.list(this.query(board.id)).pipe(
          catchError((err: CrmApiError) => {
            this.cardsError = err.message;
            return of(null);
          }),
          finalize(() => (this.loadingCards = false)),
        );
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((page) => {
      if (!page) return;
      this.opportunities = page.results;
      this.remember(page.results);
      this.buildColumns();
    });

    this.boardSelect.valueChanges.pipe(distinctUntilChanged(), takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.knownOwners.clear();
      this.knownContacts.clear();
      this.filters.reset({ ownerId: '', contact: '', status: 'open' }, { emitEvent: false });
      this.notice = '';
      this.success = '';
      this.reload$.next();
    });
    this.filters.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.reload$.next());

    this.loadBoards();
  }

  get selected(): CrmBoard | null {
    return this.boards.find((b) => b.id === this.boardSelect.value) ?? null;
  }

  get status(): CrmOpportunityStatus {
    return this.filters.controls.status.value;
  }

  get isOpenView(): boolean {
    return this.status === 'open';
  }

  get hasFilters(): boolean {
    const { ownerId, contact } = this.filters.getRawValue();
    return !!ownerId || !!contact;
  }

  get ownerOptions(): CrmOwner[] {
    return [...this.knownOwners.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  get contactOptions(): ContactOption[] {
    return [...this.knownContacts.values()].sort((a, b) => a.name.localeCompare(b.name));
  }

  get currentUser(): CrmOwner | null {
    const user = this.auth.currentUserValue;
    if (!user) return null;
    const name = `${user.firstName ?? ''} ${user.lastName ?? ''}`.trim() || user.username;
    return { id: user.id, name };
  }

  loadBoards(): void {
    this.loadingBoards = true;
    this.boardsError = '';
    this.boardsApi.list(true).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (boards) => {
        this.loadingBoards = false;
        this.boards = boards.filter((b) => b.isActive);
        const keep = this.boards.some((b) => b.id === this.boardSelect.value);
        const id = keep ? this.boardSelect.value : (this.boards[0]?.id ?? '');
        if (id === this.boardSelect.value) {
          this.reload$.next();
        } else {
          this.boardSelect.setValue(id);
        }
      },
      error: (err: CrmApiError) => {
        this.loadingBoards = false;
        this.boardsError = err.message;
      },
    });
  }

  reload(): void {
    this.reload$.next();
  }

  clearFilters(): void {
    this.filters.patchValue({ ownerId: '', contact: '' });
  }

  contact(opportunity: CrmOpportunity): CrmContact | null {
    return opportunityContact(opportunity);
  }

  overdue(opportunity: CrmOpportunity): boolean {
    return isOverdue(opportunity);
  }

  /** Etapas a las que se puede mover una tarjeta: las demás activas del mismo tablero. */
  targets(opportunity: CrmOpportunity): CrmStage[] {
    return (this.selected?.stages ?? []).filter((s) => s.id !== opportunity.stageId);
  }

  canLinkOrder(opportunity: CrmOpportunity): boolean {
    return this.salesEnabled && opportunity.status === 'won' && !opportunity.orderId && !!opportunity.customer;
  }

  move(opportunity: CrmOpportunity, stageId: string): void {
    if (!stageId || this.movingId) return;
    this.movingId = opportunity.id;
    this.notice = '';
    this.success = '';
    this.api.move(opportunity.id, stageId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.movingId = null;
        this.success = tr('CRM.OPPORTUNITY_BOARD.MOVIDA', { title: opportunity.title });
        this.reload$.next();
      },
      error: (err: CrmApiError) => {
        this.movingId = null;
        this.notice = err.fieldErrors['stageId'] ?? err.message;
        this.reload$.next();
      },
    });
  }

  create(stageId?: string): void {
    const board = this.selected;
    if (!board) return;
    const ref = this.modal.open(OpportunityDialogComponent, { centered: true, backdrop: 'static', size: 'lg' });
    (ref.componentInstance as OpportunityDialogComponent).open({
      board, owners: this.ownerOptions, currentUser: this.currentUser, stageId,
    });
    ref.result.then(() => this.done(tr('CRM.OPPORTUNITY_BOARD.CREADA')), () => this.reload$.next());
  }

  edit(opportunity: CrmOpportunity): void {
    const board = this.selected;
    if (!board) return;
    const ref = this.modal.open(OpportunityDialogComponent, { centered: true, backdrop: 'static', size: 'lg' });
    (ref.componentInstance as OpportunityDialogComponent).open({
      board, owners: this.ownerOptions, currentUser: this.currentUser, opportunity,
    });
    ref.result.then(() => this.done(tr('CRM.OPPORTUNITY_BOARD.GUARDADA')), () => this.reload$.next());
  }

  close(opportunity: CrmOpportunity): void {
    const ref = this.modal.open(CloseOpportunityDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as CloseOpportunityDialogComponent).open(opportunity, this.salesEnabled);
    ref.result.then(
      (saved: CrmOpportunity) => this.done(tr(saved.status === 'lost' ? 'CRM.OPPORTUNITY_BOARD.CERRADA_PERDIDA'
        : (opportunity.status === 'won' ? 'CRM.OPPORTUNITY_BOARD.PEDIDO_VINCULADO' : 'CRM.OPPORTUNITY_BOARD.CERRADA_GANADA'))),
      (reason: unknown) => {
        if (reason === CLOSE_DIALOG_CONVERT && opportunity.lead) {
          this.convert(opportunity.lead);
        } else {
          this.reload$.next();
        }
      },
    );
  }

  convert(lead: CrmContact): void {
    const ref = this.modal.open(ConvertLeadDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as ConvertLeadDialogComponent).open(lead);
    ref.result.then(
      (result: CrmLeadConversion) => this.done(tr(result.created ? 'CRM.LEAD_LIST.CONVERTIDO_NUEVO' : 'CRM.LEAD_LIST.CONVERTIDO_EXISTENTE',
        { name: result.customer.name })),
      () => this.reload$.next(),
    );
  }

  private done(message: string): void {
    this.notice = '';
    this.success = message;
    this.reload$.next();
  }

  private query(boardId: string): CrmOpportunityFilters {
    const { ownerId, contact, status } = this.filters.getRawValue();
    const [kind, id] = contact.split(':');
    return {
      boardId,
      status,
      ownerId: ownerId ? Number(ownerId) : undefined,
      leadId: kind === 'lead' ? id : undefined,
      customerId: kind === 'customer' ? id : undefined,
      pageSize: CRM_BOARD_PAGE_SIZE,
    };
  }

  private remember(opportunities: CrmOpportunity[]): void {
    for (const o of opportunities) {
      this.knownOwners.set(o.owner.id, o.owner);
      if (o.customer) {
        this.knownContacts.set(`customer:${o.customer.id}`, { key: `customer:${o.customer.id}`, name: o.customer.name, kind: 'customer' });
      } else if (o.lead) {
        this.knownContacts.set(`lead:${o.lead.id}`, { key: `lead:${o.lead.id}`, name: o.lead.name, kind: 'lead' });
      }
    }
  }

  private buildColumns(): void {
    const stages = this.selected?.stages ?? [];
    const column = (stage: CrmStage, cards: CrmOpportunity[]): CrmColumn => ({
      stage, cards, total: sumMoney(cards.map((c) => c.amount)),
    });
    this.columns = stages.map((stage) => column(stage, this.opportunities.filter((o) => o.stageId === stage.id)));
    // Las cerradas conservan su etapa aunque luego se archive: se agrupan aparte para no esconderlas.
    const active = new Set(stages.map((s) => s.id));
    const orphans = this.opportunities.filter((o) => !active.has(o.stageId));
    if (orphans.length) {
      const archived: CrmStage = {
        id: '', name: tr('CRM.OPPORTUNITY_BOARD.ETAPAS_ARCHIVADAS'), position: stages.length + 1, isActive: false,
        cardCount: orphans.length,
      };
      this.columns.push(column(archived, orphans));
    }
  }
}
