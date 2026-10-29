import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { PURCHASE_STATUS_LABELS, Purchase, PurchaseApiError } from '../../models/purchase';
import { PurchasesApiService } from '../../services/purchases-api.service';

/** Detalle de solo lectura de una compra; desde aquí se edita el borrador. */
@Component({
  selector: 'app-purchase-detail',
  templateUrl: './purchase-detail.component.html',
  imports: [RouterLink, DatePipe, MoneyPipe],
})
export class PurchaseDetailComponent implements OnInit {
  readonly statusLabels = PURCHASE_STATUS_LABELS;
  purchase: Purchase | null = null;
  loading = true;

  private api = inject(PurchasesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (purchase) => {
          this.purchase = purchase;
          this.loading = false;
        },
        error: (err: PurchaseApiError) => {
          this.loading = false;
          this.toastr.error(err.message);
          void this.router.navigate(['/pocketbiz/purchases']);
        },
      });
  }
}
