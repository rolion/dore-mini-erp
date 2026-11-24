import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbCollapse, NgbModal, NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { Subject, catchError, debounceTime, distinctUntilChanged, finalize, of, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { ConvertLeadDialogComponent } from '../../components/convert-lead-dialog/convert-lead-dialog.component';
import { LeadDialogComponent } from '../../components/lead-dialog/lead-dialog.component';
import { CrmApiError } from '../../models/board';
import { CrmLead, CrmLeadConversion } from '../../models/lead';
import { CrmLeadsApiService } from '../../services/crm-leads-api.service';
import { COMPACT_QUERY } from '../crm-customer-list/crm-customer-list.component';

/** `''` = todos; `'false'` = sin convertir; `'true'` = convertidos (valor del parámetro `converted`). */
export type ConvertedFilter = '' | 'false' | 'true';

/** CRM › Prospectos: lista con búsqueda, filtro de conversión, paginación del servidor y variante compacta. */
@Component({
  selector: 'app-crm-lead-list',
  templateUrl: './crm-lead-list.component.html',
  styleUrl: './crm-lead-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule, NgbCollapse, NgbPagination],
})
export class CrmLeadListComponent implements OnInit {
  readonly pageSize = 10;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly convertedControl = new FormControl<ConvertedFilter>('', { nonNullable: true });

  rows: CrmLead[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  error = '';
  success = '';
  compact = false;
  filtersCollapsed = true;

  protected applied: { search: string; converted: ConvertedFilter } = { search: '', converted: '' };

  private breakpoints = inject(BreakpointObserver);
  private api = inject(CrmLeadsApiService);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: '', totalMessage: tr('COMMON.IN_TOTAL') };
  }

  get hasFilters(): boolean {
    return !!(this.applied.search || this.applied.converted);
  }

  get activeFilterCount(): number {
    return (this.searchControl.value.trim() ? 1 : 0) + (this.convertedControl.value ? 1 : 0);
  }

  get rangeStart(): number {
    return this.total === 0 ? 0 : this.pageIndex * this.pageSize + 1;
  }

  get rangeEnd(): number {
    return Math.min((this.pageIndex + 1) * this.pageSize, this.total);
  }

  ngOnInit(): void {
    this.reload$.pipe(
      switchMap(() => {
        this.loading = true;
        this.error = '';
        const converted = this.applied.converted ? this.applied.converted === 'true' : undefined;
        return this.api.list({ search: this.applied.search, converted, page: this.pageIndex + 1, pageSize: this.pageSize }).pipe(
          catchError((err: CrmApiError) => {
            this.error = err.message;
            return of(null);
          }),
          finalize(() => (this.loading = false)),
        );
      }),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe((page) => {
      if (!page) return;
      this.rows = page.results;
      this.total = page.count;
    });

    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((state) => (this.compact = state.matches));

    // En pantalla estrecha los filtros se aplican con «Aplicar»; en escritorio, al instante.
    this.searchControl.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.applyIfWide());
    this.convertedControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.applyIfWide());

    this.reload$.next();
  }

  toggleFilters(): void {
    this.filtersCollapsed = !this.filtersCollapsed;
  }

  applyFilters(): void {
    this.filtersCollapsed = true;
    this.syncAppliedAndReload();
  }

  clearFilters(): void {
    this.searchControl.setValue('', { emitEvent: false });
    this.convertedControl.setValue('', { emitEvent: false });
    this.applyFilters();
  }

  retry(): void {
    this.reload$.next();
  }

  onCardsPage(page: number): void {
    this.onPage({ offset: page - 1 });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) return;
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  create(): void {
    const ref = this.modal.open(LeadDialogComponent, { centered: true, backdrop: 'static' });
    ref.result.then((lead: CrmLead) => this.done(tr('CRM.LEAD_LIST.CREADO', { name: lead.name })), () => undefined);
  }

  edit(lead: CrmLead): void {
    const ref = this.modal.open(LeadDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as LeadDialogComponent).edit(lead);
    ref.result.then((saved: CrmLead) => this.done(tr('CRM.LEAD_LIST.GUARDADO', { name: saved.name })), () => undefined);
  }

  convert(lead: CrmLead): void {
    const ref = this.modal.open(ConvertLeadDialogComponent, { centered: true, backdrop: 'static' });
    (ref.componentInstance as ConvertLeadDialogComponent).open({ id: lead.id, name: lead.name, phone: lead.phone });
    ref.result.then(
      (result: CrmLeadConversion) => this.done(tr(result.created ? 'CRM.LEAD_LIST.CONVERTIDO_NUEVO' : 'CRM.LEAD_LIST.CONVERTIDO_EXISTENTE',
        { name: result.customer.name })),
      () => this.reload$.next(),
    );
  }

  private done(message: string): void {
    this.success = message;
    this.reload$.next();
  }

  private applyIfWide(): void {
    if (!this.compact) this.syncAppliedAndReload();
  }

  private syncAppliedAndReload(): void {
    this.applied = { search: this.searchControl.value.trim(), converted: this.convertedControl.value };
    this.pageIndex = 0;
    this.reload$.next();
  }
}
