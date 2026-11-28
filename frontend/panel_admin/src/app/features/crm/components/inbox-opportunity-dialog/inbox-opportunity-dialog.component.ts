import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { catchError, forkJoin, of } from 'rxjs';
import { CrmApiError, CrmBoard } from '../../models/board';
import { InboxConversation } from '../../models/inbox';
import { CRM_AMOUNT_PATTERN, CRM_OPPORTUNITY_TITLE_MAX_LENGTH, CrmOpportunity } from '../../models/opportunity';
import { CrmBoardsApiService } from '../../services/crm-boards-api.service';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';

export type OpportunityMode = 'link' | 'create';

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** Vincula una oportunidad abierta del contacto o crea una nueva para él; devuelve la conversación actualizada. */
@Component({
  selector: 'app-crm-inbox-opportunity-dialog',
  templateUrl: './inbox-opportunity-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class InboxOpportunityDialogComponent implements OnInit {
  readonly titleMaxLength = CRM_OPPORTUNITY_TITLE_MAX_LENGTH;
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    mode: this.fb.control<OpportunityMode>('link'),
    opportunityId: [''],
    boardId: [''],
    title: [''],
    amount: [''],
  });

  conversation!: InboxConversation;
  opportunities: CrmOpportunity[] = [];
  boards: CrmBoard[] = [];
  loading = true;
  saving = false;
  errorMessage = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmInboxApiService);
  private boardsApi = inject(CrmBoardsApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.controls.mode.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.errorMessage = '';
    });
  }

  open(conversation: InboxConversation): void {
    this.conversation = conversation;
    if (!conversation.contact) {
      this.loading = false;
      return;
    }
    forkJoin({
      opportunities: this.api.linkableOpportunities(conversation.id).pipe(catchError(() => of([] as CrmOpportunity[]))),
      boards: this.boardsApi.list(true).pipe(catchError(() => of([] as CrmBoard[]))),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(({ opportunities, boards }) => {
      this.loading = false;
      this.opportunities = opportunities;
      this.boards = boards;
      this.form.patchValue({
        mode: opportunities.length ? 'link' : 'create',
        opportunityId: conversation.opportunity?.id ?? opportunities[0]?.id ?? '',
        boardId: boards[0]?.id ?? '',
      }, { emitEvent: false });
    });
  }

  get mode(): OpportunityMode {
    return this.form.controls.mode.value;
  }

  get canSubmit(): boolean {
    if (this.saving || this.loading || !this.conversation.contact) return false;
    const v = this.form.getRawValue();
    if (v.mode === 'link') return !!v.opportunityId;
    return !!v.boardId && !notBlank(this.form.controls.title) && CRM_AMOUNT_PATTERN.test(v.amount);
  }

  save(): void {
    if (!this.canSubmit) return;
    const v = this.form.getRawValue();
    const request = v.mode === 'link'
      ? this.api.setOpportunity(this.conversation.id, v.opportunityId)
      : this.api.createOpportunity(this.conversation.id, { boardId: v.boardId, title: v.title, amount: v.amount });
    this.run(request);
  }

  unlink(): void {
    this.run(this.api.setOpportunity(this.conversation.id, null));
  }

  private run(request: ReturnType<CrmInboxApiService['setOpportunity']>): void {
    this.saving = true;
    this.errorMessage = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.saving = false;
        this.activeModal.close(updated);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        this.errorMessage = err.message;
      },
    });
  }
}
