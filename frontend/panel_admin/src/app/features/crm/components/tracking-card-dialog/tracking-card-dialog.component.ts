import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormBuilder, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Subject, catchError, debounceTime, distinctUntilChanged, forkJoin, map, of, switchMap, tap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { CrmApiError } from '../../models/board';
import { ActivityDialogComponent } from '../activity-dialog/activity-dialog.component';
import {
  CRM_OPPORTUNITY_DESCRIPTION_MAX_LENGTH, CRM_OPPORTUNITY_TITLE_MAX_LENGTH, CrmOpportunity,
} from '../../models/opportunity';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { CrmOpportunitiesApiService } from '../../services/crm-opportunities-api.service';

const SEARCH_PAGE_SIZE = 10;

/** Lo que el tablero le pasa al diálogo al abrirlo. */
export interface TrackingCardDialogContext {
  boardId: string;
  stageId: string;
  /** Tarjeta que se ve y edita; sin ella se crea una nueva. */
  card?: CrmOpportunity;
}

/** Cliente o prospecto elegible; `group` es el texto del encabezado del grupo en el selector. */
export interface TrackingContactOption {
  key: string;
  id: string;
  kind: 'lead' | 'customer';
  name: string;
  phone: string;
  group: string;
}

function notBlank(control: AbstractControl<string>): ValidationErrors | null {
  return control.value.trim() ? null : { required: true };
}

type CardField = 'name' | 'contact' | 'description';

/**
 * Alta de una tarjeta de seguimiento en una columna o, con `card`, su ficha: se ve y se edita nombre y descripción
 * (el cliente o prospecto queda fijo) y desde ahí se agrega una actividad. Devuelve la tarjeta guardada.
 */
@Component({
  selector: 'app-crm-tracking-card-dialog',
  templateUrl: './tracking-card-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, NgSelectModule],
})
export class TrackingCardDialogComponent implements OnInit {
  readonly nameMaxLength = CRM_OPPORTUNITY_TITLE_MAX_LENGTH;
  readonly descriptionMaxLength = CRM_OPPORTUNITY_DESCRIPTION_MAX_LENGTH;
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    name: ['', [notBlank, Validators.maxLength(CRM_OPPORTUNITY_TITLE_MAX_LENGTH)]],
    contact: this.fb.control<TrackingContactOption | null>(null, Validators.required),
    description: ['', Validators.maxLength(CRM_OPPORTUNITY_DESCRIPTION_MAX_LENGTH)],
  });

  context!: TrackingCardDialogContext;
  contacts: TrackingContactOption[] = [];
  contactsLoading = false;
  readonly contactSearch$ = new Subject<string>();
  saving = false;
  errorMessage = '';
  serverErrors: Partial<Record<CardField, string>> = {};

  readonly activeModal = inject(NgbActiveModal);
  private modal = inject(NgbModal);
  private api = inject(CrmOpportunitiesApiService);
  private leadsApi = inject(CrmLeadsApiService);
  private customersApi = inject(CrmCustomersApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.serverErrors = {};
      this.errorMessage = '';
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
    this.contactSearch$.next('');
  }

  open(context: TrackingCardDialogContext): void {
    this.context = context;
    const card = context.card;
    if (!card) return;
    const person = card.customer ?? card.lead;
    this.form.controls.contact.disable({ emitEvent: false });
    this.form.patchValue({
      name: card.title,
      description: card.description,
      contact: person ? {
        key: `${card.customer ? 'customer' : 'lead'}:${person.id}`, id: person.id, kind: card.customer ? 'customer' : 'lead',
        name: person.name, phone: person.phone ?? '', group: '',
      } : null,
    }, { emitEvent: false });
  }

  get isEdit(): boolean {
    return !!this.context?.card;
  }

  /** «Agregar actividad» de la tarjeta: abre el registro de actividades encima de esta ficha. */
  addActivity(): void {
    const card = this.context.card;
    if (!card) return;
    const ref = this.modal.open(ActivityDialogComponent, { centered: true, backdrop: 'static', scrollable: true });
    (ref.componentInstance as ActivityDialogComponent).open({ type: 'opportunity', id: card.id, name: card.title });
    ref.result.then(() => undefined, () => undefined);
  }

  invalid(field: CardField): boolean {
    const control = this.form.controls[field];
    return (control.invalid && (control.touched || control.dirty)) || !!this.serverErrors[field];
  }

  onSubmit(): void {
    if (this.form.invalid || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    const value = this.form.getRawValue();
    const contact = value.contact;
    this.saving = true;
    const card = this.context.card;
    const request = card
      ? this.api.update(card.id, { title: value.name.trim(), description: value.description.trim() })
      : this.api.create({
      boardId: this.context.boardId,
      stageId: this.context.stageId,
      leadId: contact?.kind === 'lead' ? contact.id : undefined,
      customerId: contact?.kind === 'customer' ? contact.id : undefined,
      title: value.name.trim(),
      description: value.description.trim(),
    });
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (saved: CrmOpportunity) => {
        this.saving = false;
        this.activeModal.close(saved);
      },
      error: (err: CrmApiError) => {
        this.saving = false;
        const f = err.fieldErrors;
        this.serverErrors = { name: f['title'], contact: f['leadId'] ?? f['customerId'], description: f['description'] };
        const hasField = Object.values(this.serverErrors).some(Boolean);
        this.errorMessage = hasField && err.status === 400 ? '' : err.message;
      },
    });
  }

  private searchContacts(term: string) {
    const customers$ = this.customersApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
      map((page): TrackingContactOption[] => page.results.map((c) => ({
        key: `customer:${c.id}`, id: c.id, kind: 'customer', name: c.name, phone: c.phone ?? '', group: tr('CRM.TRACKING.GRUPO_CLIENTES'),
      }))),
      catchError(() => of([] as TrackingContactOption[])),
    );
    const leads$ = this.leadsApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
      map((page): TrackingContactOption[] => page.results.map((l) => ({
        key: `lead:${l.id}`, id: l.id, kind: 'lead', name: l.name, phone: l.phone ?? '', group: tr('CRM.TRACKING.GRUPO_PROSPECTOS'),
      }))),
      catchError(() => of([] as TrackingContactOption[])),
    );
    return forkJoin([customers$, leads$]).pipe(map(([customers, leads]) => [...customers, ...leads]));
  }
}
