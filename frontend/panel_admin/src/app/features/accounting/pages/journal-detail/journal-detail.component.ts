import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { AccountingApiError } from '../../models/accounting';
import { JournalEntryDetail, SOURCE_CLASSES, journalOriginLink, sourceLabel } from '../../models/journal';
import { JournalApiService } from '../../services/journal-api.service';
import { JournalReverseDialogComponent } from '../../components/journal-reverse-dialog/journal-reverse-dialog.component';

/** Detalle de un asiento: líneas, origen, usuario y reversión vinculada. Nunca se edita ni se borra. */
@Component({
  selector: 'app-journal-detail',
  templateUrl: './journal-detail.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe],
})
export class JournalDetailComponent implements OnInit {
  entry: JournalEntryDetail | null = null;
  loading = true;
  errorMessage = '';
  notFound = false;
  /** Asiento de reversión recién creado (aviso de éxito con enlace). */
  createdReversalId: string | null = null;
  justCreated = false;

  private api = inject(JournalApiService);
  private route = inject(ActivatedRoute);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.justCreated = this.route.snapshot.queryParamMap.get('created') === '1';
    this.route.paramMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.load());
  }

  private get id(): string {
    return this.route.snapshot.paramMap.get('id') ?? '';
  }

  retry(): void {
    this.load();
  }

  private load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.notFound = false;
    this.api.get(this.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (entry) => {
        this.entry = entry;
        this.loading = false;
      },
      error: (err: AccountingApiError) => {
        this.errorMessage = err.message;
        this.notFound = err.status === 404;
        this.loading = false;
      },
    });
  }

  get originText(): string {
    return this.entry ? sourceLabel(this.entry.source) : '';
  }

  get originClass(): string {
    return this.entry ? SOURCE_CLASSES[this.entry.source] : '';
  }

  get originLink(): string[] | null {
    return journalOriginLink(this.entry?.origin ?? null);
  }

  openReverse(): void {
    const entry = this.entry;
    if (!entry) return;
    const ref = this.modal.open(JournalReverseDialogComponent, { backdrop: 'static' });
    (ref.componentInstance as JournalReverseDialogComponent).init(entry);
    ref.result.then(
      (reversal: JournalEntryDetail) => {
        this.createdReversalId = reversal.id;
        this.justCreated = false;
        this.load();
      },
      () => undefined, // cerrado sin revertir
    );
  }
}
