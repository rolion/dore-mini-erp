import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { Subject, switchMap } from 'rxjs';
import { AccountingApiError } from '../../models/accounting';
import { Entry, ORIGIN_CLASSES, formatAmount, originLabel, sourceLink } from '../../models/entry';
import { EntriesApiService } from '../../services/entries-api.service';

/** Detalle de una entrada del libro (solo lectura). */
@Component({
  selector: 'app-entry-detail',
  templateUrl: './entry-detail.component.html',
  imports: [TranslatePipe, RouterLink, DatePipe],
})
export class EntryDetailComponent implements OnInit {
  entry: Entry | null = null;
  loading = true;
  errorMessage = '';
  notFound = false;

  private api = inject(EntriesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          this.notFound = false;
          return this.api.get(this.route.snapshot.paramMap.get('id') ?? '');
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({ next: (entry) => this.show(entry), error: (err: AccountingApiError) => this.fail(err) });
    this.reload$.next();
  }

  retry(): void {
    this.reload$.next();
  }

  get originText(): string {
    return this.entry ? originLabel(this.entry.origin) : '';
  }

  get originClass(): string {
    return this.entry ? ORIGIN_CLASSES[this.entry.origin] : '';
  }

  get amountText(): string {
    return this.entry ? formatAmount(this.entry.amount, this.entry.currency) : '';
  }

  get link(): string[] | null {
    return this.entry ? sourceLink(this.entry) : null;
  }

  private show(entry: Entry): void {
    this.entry = entry;
    this.loading = false;
  }

  private fail(err: AccountingApiError): void {
    this.loading = false;
    this.notFound = err.status === 404;
    this.errorMessage = err.message;
  }
}
