import { DatePipe } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, inject, viewChild } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbModal, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, interval, of, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { InboxContactDialogComponent } from '../../components/inbox-contact-dialog/inbox-contact-dialog.component';
import { InboxOpportunityDialogComponent } from '../../components/inbox-opportunity-dialog/inbox-opportunity-dialog.component';
import { CrmApiError } from '../../models/board';
import { InboxConversation, InboxMessage, InboxScope, InboxTemplate } from '../../models/inbox';
import { CrmOwner } from '../../models/opportunity';
import { CrmInboxApiService } from '../../services/crm-inbox-api.service';
import { CrmUsersApiService } from '../../services/crm-users-api.service';

export const INBOX_SCOPES: readonly InboxScope[] = ['mine', 'unassigned', 'all'];
/** Cada cuánto se consultan mensajes nuevos con la pestaña visible (DDR: sin tiempo real). */
export const INBOX_POLL_MS = 10_000;
const BODY_MAX = 4096;

/** CRM › Bandeja: conversaciones de WhatsApp, responder, asignar y vincular a contacto y oportunidad. */
@Component({
  selector: 'app-crm-inbox',
  templateUrl: './crm-inbox.component.html',
  styleUrl: './crm-inbox.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgbPagination, DatePipe],
})
export class CrmInboxComponent implements OnInit {
  readonly pageSize = 20;
  readonly scopes = INBOX_SCOPES;
  readonly bodyMax = BODY_MAX;
  readonly scopeControl = new FormControl<InboxScope>('all', { nonNullable: true });
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly replyControl = new FormControl('', { nonNullable: true });
  readonly templateControl = new FormControl('', { nonNullable: true });

  rows: InboxConversation[] = [];
  total = 0;
  page = 1;
  loading = false;
  error = '';
  selected: InboxConversation | null = null;
  messages: InboxMessage[] = [];
  threadLoading = false;
  threadError = '';
  sending = false;
  actionError = '';
  success = '';
  users: CrmOwner[] = [];
  templates: InboxTemplate[] = [];

  private api = inject(CrmInboxApiService);
  private usersApi = inject(CrmUsersApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<boolean>();
  private thread = viewChild<ElementRef<HTMLElement>>('thread');

  get hasFilters(): boolean {
    return !!this.searchControl.value.trim() || this.scopeControl.value !== 'all';
  }

  get connectionDown(): boolean {
    return this.selected?.connectionActive === false;
  }

  ngOnInit(): void {
    this.reload$.pipe(
      switchMap((silent) => {
        if (!silent) {
          this.loading = true;
          this.error = '';
        }
        return this.api.list({
          scope: this.scopeControl.value, search: this.searchControl.value.trim() || undefined,
          page: this.page, pageSize: this.pageSize,
        }).pipe(catchError((err: CrmApiError) => {
          if (!silent) this.error = err.message;
          return of(null);
        }));
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((result) => {
      this.loading = false;
      if (result) {
        this.rows = result.results;
        this.total = result.count;
      }
    });

    this.scopeControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refresh(1));
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.refresh(1));
    this.usersApi.list().pipe(catchError(() => of([] as CrmOwner[])), takeUntilDestroyed(this.destroyRef))
      .subscribe((users) => (this.users = users));
    this.api.approvedTemplates().pipe(catchError(() => of([] as InboxTemplate[])), takeUntilDestroyed(this.destroyRef))
      .subscribe((templates) => (this.templates = templates));
    // El temporizador vive mientras exista el componente; solo consulta con la pestaña visible.
    interval(INBOX_POLL_MS).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.poll());
    this.reload$.next(false);
  }

  onPage(page: number): void {
    this.refresh(page);
  }

  retry(): void {
    this.reload$.next(false);
  }

  clearFilters(): void {
    this.scopeControl.setValue('all', { emitEvent: false });
    this.searchControl.setValue('', { emitEvent: false });
    this.refresh(1);
  }

  open(conversation: InboxConversation): void {
    this.selected = conversation;
    this.threadError = '';
    this.actionError = '';
    this.success = '';
    this.replyControl.setValue('');
    this.messages = [];
    this.threadLoading = true;
    this.loadThread(conversation.id, false);
  }

  /** Vuelve a la lista (solo se ve en pantallas angostas, donde hay un panel a la vez). */
  back(): void {
    this.selected = null;
  }

  send(): void {
    const conversation = this.selected;
    const body = this.replyControl.value.trim();
    if (!conversation || !body || this.sending) return;
    this.deliver(this.api.sendText(conversation.id, body), () => this.replyControl.setValue(''));
  }

  sendTemplate(): void {
    const conversation = this.selected;
    const templateId = this.templateControl.value;
    if (!conversation || !templateId || this.sending) return;
    this.deliver(this.api.sendTemplate(conversation.id, templateId), () => this.templateControl.setValue(''));
  }

  resend(message: InboxMessage): void {
    const conversation = this.selected;
    if (!conversation) return;
    this.actionError = '';
    this.api.retry(conversation.id, message.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => this.loadThread(conversation.id, true),
      error: (err: CrmApiError) => (this.actionError = err.message),
    });
  }

  assign(value: string): void {
    const conversation = this.selected;
    if (!conversation) return;
    this.change(this.api.assign(conversation.id, value ? Number(value) : null), 'CRM.INBOX.RESPONSABLE_ACTUALIZADO');
  }

  linkContact(): void {
    const conversation = this.selected;
    if (!conversation) return;
    const ref = this.modal.open(InboxContactDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as InboxContactDialogComponent).open(conversation);
    ref.result.then((updated: InboxConversation) => this.applied(updated, 'CRM.INBOX.CONTACTO_VINCULADO'), () => undefined);
  }

  linkOpportunity(): void {
    const conversation = this.selected;
    if (!conversation) return;
    const ref = this.modal.open(InboxOpportunityDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as InboxOpportunityDialogComponent).open(conversation);
    ref.result.then((updated: InboxConversation) => this.applied(updated, 'CRM.INBOX.OPORTUNIDAD_ACTUALIZADA'), () => undefined);
  }

  private change(request: Observable<InboxConversation>, messageKey: string): void {
    this.actionError = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => this.applied(updated, messageKey),
      error: (err: CrmApiError) => {
        this.actionError = err.message;
        this.success = '';
      },
    });
  }

  private applied(updated: InboxConversation, messageKey: string): void {
    this.selected = { ...updated, connectionActive: updated.connectionActive ?? this.selected?.connectionActive ?? null };
    this.success = tr(messageKey);
    this.reload$.next(true);
  }

  private deliver(request: Observable<InboxMessage>, done: () => void): void {
    const conversation = this.selected;
    if (!conversation) return;
    this.sending = true;
    this.actionError = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => {
        this.sending = false;
        done();
        this.loadThread(conversation.id, true);
        this.reload$.next(true);
      },
      error: (err: CrmApiError) => {
        this.sending = false;
        this.actionError = err.message;
        // La ventana pudo cerrarse mientras se escribía: refresca el estado para mostrar las plantillas.
        if (err.code === 'window_closed') this.refreshSelected(conversation.id);
      },
    });
  }

  private refreshSelected(conversationId: string): void {
    this.api.get(conversationId).pipe(catchError(() => of(null)), takeUntilDestroyed(this.destroyRef)).subscribe((fresh) => {
      if (fresh && this.selected?.id === conversationId) this.selected = fresh;
    });
  }

  private loadThread(conversationId: string, silent: boolean): void {
    this.api.get(conversationId).pipe(
      switchMap((detail) => {
        if (this.selected?.id === conversationId) this.selected = detail;
        return this.api.messages(conversationId);
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: (messages) => {
        if (this.selected?.id !== conversationId) return;
        this.threadLoading = false;
        const changed = messages.length !== this.messages.length
          || messages.some((m, i) => m.id !== this.messages[i]?.id || m.status !== this.messages[i]?.status);
        if (changed) {
          this.messages = messages;
          queueMicrotask(() => this.scrollToEnd());
        }
      },
      error: (err: CrmApiError) => {
        this.threadLoading = false;
        if (!silent) this.threadError = err.message;
      },
    });
  }

  private poll(): void {
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') return;
    this.reload$.next(true);
    if (this.selected) this.loadThread(this.selected.id, true);
  }

  private scrollToEnd(): void {
    const element = this.thread()?.nativeElement;
    if (element) element.scrollTop = element.scrollHeight;
  }

  private refresh(page: number): void {
    this.page = page;
    this.reload$.next(false);
  }
}
