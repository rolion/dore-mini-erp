import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { AuthService } from '../../../../core/service/auth.service';
import { InventoryApiError } from '../../models/api-error';
import {
  MOVEMENT_STATUS_LABELS,
  SOURCE_ROUTES,
  StockMovementDetail,
  movementTypeLabel,
} from '../../models/movement';
import {
  MovementReverseDialogComponent,
  ReversibleMovement,
} from '../../components/movement-reverse-dialog/movement-reverse-dialog.component';
import { MovementsApiService } from '../../services/movements-api.service';

@Component({
  selector: 'app-movement-detail',
  templateUrl: './movement-detail.component.html',
  imports: [RouterLink, DatePipe],
})
export class MovementDetailComponent implements OnInit {
  readonly typeLabel = movementTypeLabel;
  readonly statusLabels = MOVEMENT_STATUS_LABELS;

  movement: StockMovementDetail | null = null;
  loading = true;
  errorMessage = '';
  notFound = false;
  successMessage = '';

  private api = inject(MovementsApiService);
  private route = inject(ActivatedRoute);
  private auth = inject(AuthService);
  private modal = inject(NgbModal);
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

  /** Datos para el diálogo de reversión (cantidad sin signo y almacén ya nombrados). */
  private reversible(movement: StockMovementDetail): ReversibleMovement {
    return {
      id: movement.id,
      reference: movement.reference,
      typeLabel: movementTypeLabel(movement),
      productName: movement.product.name,
      warehouseName: movement.warehouse.name,
      quantity: movement.quantity,
      unitAbbreviation: movement.unitAbbreviation,
      kind: movement.kind,
    };
  }

  /** «Revertir» solo se ofrece si el servidor lo permite; la barrera real es el backend. */
  get canReverse(): boolean {
    return this.movement?.status === 'confirmed' && this.movement.reversal.allowed;
  }

  /** Por qué un movimiento confirmado no se puede revertir desde aquí (venta o compra). */
  get reverseBlockedMessage(): string {
    const movement = this.movement;
    return movement?.status === 'confirmed' && !movement.reversal.allowed ? (movement.reversal.message ?? '') : '';
  }

  async reverse(): Promise<void> {
    const movement = this.movement;
    if (!movement || !this.canReverse) return;
    const ref = this.modal.open(MovementReverseDialogComponent, { backdrop: 'static' });
    (ref.componentInstance as MovementReverseDialogComponent).init(this.reversible(movement));
    try {
      await ref.result;
    } catch {
      return; // «Volver»: no cambia nada.
    }
    this.successMessage = 'Movimiento revertido';
    this.load();
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
