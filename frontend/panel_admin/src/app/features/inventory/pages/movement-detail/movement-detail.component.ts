import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { AuthService } from '../../../../core/service/auth.service';
import { InventoryApiError } from '../../models/api-error';
import {
  MOVEMENT_KIND_LABELS,
  MOVEMENT_STATUS_LABELS,
  SOURCE_ROUTES,
  StockMovementDetail,
} from '../../models/movement';
import { MovementsApiService } from '../../services/movements-api.service';

@Component({
  selector: 'app-movement-detail',
  templateUrl: './movement-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class MovementDetailComponent implements OnInit {
  readonly kindLabels = MOVEMENT_KIND_LABELS;
  readonly statusLabels = MOVEMENT_STATUS_LABELS;

  movement: StockMovementDetail | null = null;
  loading = true;
  errorMessage = '';
  notFound = false;

  private api = inject(MovementsApiService);
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);
  private destroyRef = inject(DestroyRef);

  /** Empresa de la sesión: el movimiento pertenece siempre a ella (la API filtra por empresa). */
  get companyName(): string {
    return this.auth.currentUserValue?.company?.name ?? '—';
  }

  get sourceLink(): string[] | null {
    const source = this.movement?.source;
    const route = source ? SOURCE_ROUTES[source.type] : undefined;
    return source && source.available && route ? route(source.id) : null;
  }

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.api
      .get(id)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (movement) => {
          this.movement = movement;
          this.loading = false;
        },
        error: (err: InventoryApiError) => {
          this.loading = false;
          this.notFound = err.status === 404;
          this.errorMessage = err.message;
        },
      });
  }
}
