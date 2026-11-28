import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgbActiveModal, NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, map, of, switchMap, tap } from 'rxjs';
import { CrmApiError } from '../../models/board';
import { InboxConversation } from '../../models/inbox';
import { CrmContact } from '../../models/lead';
import { CrmCustomersApiService } from '../../services/crm-customers-api.service';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';
import { LeadDialogComponent } from '../lead-dialog/lead-dialog.component';
import { CrmLead } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';

type ContactKind = 'lead' | 'customer';
const SEARCH_PAGE_SIZE = 20;

/** Vincula (o quita) el cliente o prospecto de una conversación; se cierra devolviendo la conversación actualizada. */
@Component({
  selector: 'app-crm-inbox-contact-dialog',
  templateUrl: './inbox-contact-dialog.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, NgSelectModule],
})
export class InboxContactDialogComponent implements OnInit {
  private fb = inject(FormBuilder).nonNullable;
  readonly form = this.fb.group({
    kind: this.fb.control<ContactKind>('customer'),
    contact: this.fb.control<CrmContact | null>(null, Validators.required),
  });

  conversation!: InboxConversation;
  contacts: CrmContact[] = [];
  contactsLoading = false;
  readonly contactSearch$ = new Subject<string>();
  saving = false;
  errorMessage = '';

  readonly activeModal = inject(NgbActiveModal);
  private api = inject(CrmInboxApiService);
  private leadsApi = inject(CrmLeadsApiService);
  private customersApi = inject(CrmCustomersApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.form.controls.kind.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.form.controls.contact.setValue(null);
      this.contacts = [];
    });
    this.contactSearch$.pipe(
      debounceTime(250),
      distinctUntilChanged(),
      tap(() => (this.contactsLoading = true)),
      switchMap((term) => this.search(term.trim())),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((contacts) => {
      this.contactsLoading = false;
      this.contacts = contacts;
    });
  }

  open(conversation: InboxConversation): void {
    this.conversation = conversation;
    this.form.controls.kind.setValue(conversation.contact?.type ?? 'customer', { emitEvent: false });
  }

  get kind(): ContactKind {
    return this.form.controls.kind.value;
  }

  save(): void {
    const contact = this.form.controls.contact.value;
    if (!contact || this.saving) {
      this.form.markAllAsTouched();
      return;
    }
    this.submit({ type: this.kind, id: contact.id });
  }

  /** Teléfono desconocido: crea el prospecto (con el teléfono de la conversación) y lo vincula. */
  createLead(): void {
    if (this.saving) return;
    const ref = this.modal.open(LeadDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as LeadDialogComponent).form.patchValue({ phone: `+${this.conversation.phone}` });
    ref.result.then((lead: CrmLead) => this.submit({ type: 'lead', id: lead.id }), () => undefined);
  }

  remove(): void {
    this.submit(null);
  }

  private submit(contact: { type: ContactKind; id: string } | null): void {
    this.saving = true;
    this.errorMessage = '';
    this.api.setContact(this.conversation.id, contact).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
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

  private search(term: string): Observable<CrmContact[]> {
    const found: Observable<CrmContact[]> = this.kind === 'lead'
      ? this.leadsApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
        map((page) => page.results.map((l) => ({ id: l.id, name: l.name, phone: l.phone }))))
      : this.customersApi.list({ search: term, pageSize: SEARCH_PAGE_SIZE }).pipe(
        map((page) => page.results.map((c) => ({ id: c.id, name: c.name, phone: c.phone }))));
    return found.pipe(catchError(() => of([])));
  }
}
