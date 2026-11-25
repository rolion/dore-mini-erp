import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, map, of, switchMap, tap } from 'rxjs';
import { CrmApiError, CrmBoard, CrmStage } from '../../models/board';
import { CrmContact } from '../../models/lead';
import {
  CRM_AMOUNT_PATTERN, CRM_OPPORTUNITY_TITLE_MAX_LENGTH, CrmOpportunity, CrmOpportunityUpdate, CrmOwner,
} from '../../models/opportunity';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';

export type ContactKind = 'lead' | 'customer';

/** Lo que el tablero le pasa al diálogo al abrirlo. */
export interface OpportunityDialogContext {
  board: CrmBoard;
  /** Responsables conocidos (usuarios vistos en el tablero); el usuario actual se agrega solo. */
  owners: CrmOwner[];
  currentUser: CrmOwner | null;
  /** Oportunidad que se edita; sin ella se crea. */
  opportunity?: CrmOpportunity;
  /** Etapa inicial sugerida (p. ej. la columna desde la que se abre). */
  stageId?: string;
}

const SEARCH_PAGE_SIZE = 20;

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

/** `2026-11-24T15:30:00Z` → valor de `input type="datetime-local"` en la hora local. */
export function toLocalInput(iso: string | null): string {
  if (!iso) return '';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  const pad = (n: number): string => String(n).padStart(2, '0');
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}

/** Valor de `datetime-local` (hora local) → ISO 8601 en UTC; vacío → `null`. */
export function fromLocalInput(value: string): string | null {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date.toISOString();
}

interface OpportunityFormValue {
  contactKind: ContactKind;
  contact: CrmContact | null;
  title: string;
  amount: string;
  nextActionAt: string;
  ownerId: string;
  stageId: string;
}

type OpportunityField = 'contact' | 'title' | 'amount' | 'nextActionAt' | 'ownerId' | 'stageId';

/** Alta o edición de una oportunidad; se cierra devolviendo la oportunidad guardada. */
@Component({
  selector: 'app-crm-opportunity-dialog',
  templateUrl: './opportunity-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, NgSelectModule],
})
export class OpportunityDialogComponent implements OnInit {
  readonly titleMaxLength = CRM_OPPORTUNITY_TITLE_MAX_LENGTH;
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    contactKind: this.fb.control<ContactKind>('lead'),
    contact: this.fb.control<CrmContact | null>(null, Validators.required),
    title: ['', [notBlank, Validators.maxLength(CRM_OPPORTUNITY_TITLE_MAX_LENGTH)]],
    amount: ['', [Validators.required, Validators.pattern(CRM_AMOUNT_PATTERN)]],
    nextActionAt: [''],
    ownerId: [''],
    stageId: [''],
  });

  context!: OpportunityDialogContext;
  contacts: CrmContact[] = [];
  contactsLoading = false;
  readonly contactSearch$ = new Subject<string>();
  saving = false;
  errorMessage = '';
  conflict = false;
  serverErrors: Partial<Record<OpportunityField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmOpportunitiesApiService);
  private leadsApi = inject(CrmLeadsApiService);
  private customersApi = inject(CrmCustomersApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.errorMessage = '';
    });
    this.form.controls.contactKind.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.form.controls.contact.setValue(null);
      this.contacts = [];
    });
    this.contactSearch$.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      tap(() => (this.contactsLoading = true)),
      switchMap((term) => this.searchContacts(term.trim())),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((contacts) => {
      this.contactsLoading = false;
      this.contacts = contacts;
    });
  }

  open(context: OpportunityDialogContext): void {
    this.context = context;
    const opportunity = context.opportunity;
    if (opportunity) {
      this.form.controls.contact.disable({ emitEvent: false });
      this.form.controls.contactKind.disable({ emitEvent: false });
      this.form.controls.stageId.disable({ emitEvent: false });
      this.form.patchValue({
        contactKind: opportunity.customer ? 'customer' : 'lead',
        contact: opportunity.customer ?? opportunity.lead,
        title: opportunity.title,
        amount: opportunity.amount,
        nextActionAt: toLocalInput(opportunity.nextActionAt),
        ownerId: String(opportunity.owner.id),
        stageId: opportunity.stageId,
      }, { emitEvent: false });
    } else {
      const stageId = context.stageId ?? context.board.stages[0]?.id ?? '';
      this.form.patchValue({ stageId, ownerId: context.currentUser ? String(context.currentUser.id) : '' }, { emitEvent: false });
    }
  }

  get isEdit(): boolean {
    return !!this.context.opportunity;
  }

  get stages(): CrmStage[] {
    return this.context.board.stages;
  }

  /** Responsables a elegir: el usuario actual, el actual de la oportunidad y los vistos en el tablero, sin repetir. */
  get ownerOptions(): CrmOwner[] {
    const all = [this.context.currentUser, this.context.opportunity?.owner, ...this.context.owners]
      .filter((o): o is CrmOwner => !!o);
    return all.filter((owner, index) => all.findIndex((o) => o.id === owner.id) === index);
  }

  get contactKind(): ContactKind {
    return this.form.controls.contactKind.value;
  }

  invalid(field: OpportunityField): boolean {
    const control = field === 'contact' ? this.form.controls.contact : this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    this.saving = true;
    this.conflict = false;
    this.request(value).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        const f = err.fieldErrors;
        this.serverErrors = {
          contact: f['leadId'] ?? f['customerId'], title: f['title'], amount: f['amount'],
          nextActionAt: f['nextActionAt'], ownerId: f['ownerId'], stageId: f['stageId'] ?? f['boardId'],
        };
        this.conflict = err.status === 409;
        const hasField = Object.values(this.serverErrors).some(Boolean);
        this.errorMessage = hasField && err.status === 400 ? '' : err.message;
      },
    });
  }

  private request(value: OpportunityFormValue): Observable<CrmOpportunity> {
    const ownerId = value.ownerId ? Number(value.ownerId) : undefined;
    const nextActionAt = fromLocalInput(value.nextActionAt);
    const opportunity = this.context.opportunity;
    if (opportunity) {
      const changes: CrmOpportunityUpdate = { title: value.title.trim(), amount: value.amount, nextActionAt };
      if (ownerId !== undefined && ownerId !== opportunity.owner.id) changes.ownerId = ownerId;
      return this.api.update(opportunity.id, changes);
    }
    const contactId = value.contact?.id;
    return this.api.create({
      boardId: this.context.board.id,
      stageId: value.stageId || undefined,
      leadId: value.contactKind === 'lead' ? contactId : undefined,
      customerId: value.contactKind === 'customer' ? contactId : undefined,
      title: value.title.trim(),
      amount: value.amount,
      nextActionAt,
      ownerId,
    });
  }

  private searchContacts(term: string): Observable<CrmContact[]> {
    const search: Observable<CrmContact[]> = this.contactKind === 'lead'
      ? this.leadsApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
        map((page) => page.results.map((l) => ({ id: l.id, name: l.name, phone: l.phone }))))
      : this.customersApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
        map((page) => page.results.map((c) => ({ id: c.id, name: c.name, phone: c.phone }))));
    return search.pipe(catchError(() => of([])));
  }
}
