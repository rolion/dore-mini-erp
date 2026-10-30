import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import {
  PURCHASE_STATUS_CLASSES,
  PURCHASE_STATUS_LABELS,
  PurchaseApiError,
  PurchaseStatus,
  PurchaseSummary,
} from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';
import { SuppliersApiService } from '../../services/suppliers-api.service';

/** Lista de compras (solo lectura). Con `?supplierId=` muestra únicamente las de ese proveedor. */
@Component({
  selector: 'app-purchase-list',
  templateUrl: './purchase-list.component.html',
  styleUrl: './purchase-list.component.scss',
  imports: [RouterLink, NgxDatatableModule, DatePipe, MoneyPipe],
})
export class PurchaseListComponent implements OnInit {
  readonly pageSize = 10;
  rows: PurchaseSummary[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;
  errorMessage = '';
  supplierId: string | null = null;
  supplierName = '';

  private api = inject(PurchasesApiService);
  private suppliersApi = inject(SuppliersApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  get emptyMessage(): string {
    return this.supplierId
      ? 'No hay compras para este proveedor.'
      : 'Aún no hay compras. Crea la primera con «Nueva compra».';
  }

  get messages(): { emptyMessage: string; totalMessage: string } {
    return { emptyMessage: this.emptyMessage, totalMessage: 'en total' };
  }

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api
            .list({ supplierId: this.supplierId ?? undefined, page: this.pageIndex + 1, pageSize: this.pageSize })
            .pipe(
              catchError((err: PurchaseApiError) => {
                this.errorMessage = err.message;
                return EMPTY;
              }),
              finalize(() => (this.loading = false)),
            );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
      });

    this.route.queryParamMap.pipe(takeUntilDestroyed(this.destroyRef)).subscribe((params) => {
      this.supplierId = params.get('supplierId');
      this.supplierName = '';
      this.pageIndex = 0;
      if (this.supplierId) {
        this.loadSupplierName(this.supplierId);
      }
      this.reload$.next();
    });
  }

  onPage(event: { offset: number }): void {
    // ngx-datatable también emite `page` al inicializarse; sin cambio de página no se vuelve a pedir.
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  statusClass(status: PurchaseStatus): string {
    return PURCHASE_STATUS_CLASSES[status];
  }

  statusLabel(status: PurchaseStatus): string {
    return PURCHASE_STATUS_LABELS[status];
  }

  retry(): void {
    this.reload$.next();
  }

  clearSupplierFilter(): void {
    void this.router.navigate(['/pocketbiz/purchases']);
  }

  private loadSupplierName(id: string): void {
    this.suppliersApi
      .get(id)
      .pipe(
        catchError(() => EMPTY),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((supplier) => (this.supplierName = supplier.name));
  }
}
