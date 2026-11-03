import { Component, DestroyRef, Input, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { EMPTY, catchError, filter, map, switchMap, take } from 'rxjs';
import { ModulesService } from '../../../../core/service/modules.service';
import { MoneyPipe } from '../../../../shared/pipes/money.pipe';
import { ValuationApiService } from '../../../inventory/services/valuation-api.service';
import { COST_ORIGIN_LABELS, MovementValuation } from '../../models/movement-valuation';
import { MovementValuationApiService } from '../../services/movement-valuation-api.service';

export const NOT_VALUED_MESSAGE = 'Este movimiento no tiene costo propio: es anterior a la valoración adoptada.';

/**
 * Sección «Valoración» de solo lectura para un documento (recepción) o un movimiento. Solo aparece con Costeo
 * habilitado y una valoración adoptada; el backend es quien impide ver o cambiar datos de otra empresa.
 */
@Component({
  selector: 'app-movement-valuation-section',
  templateUrl: './movement-valuation-section.component.html',
  imports: [MoneyPipe],
})
export class MovementValuationSectionComponent implements OnInit {
  /** Documento de origen (p. ej. `purchase_receipt`) y su id; o bien el id de un movimiento. */
  @Input() sourceType = '';
  @Input() sourceId = '';
  @Input() movementId = '';

  readonly originLabels = COST_ORIGIN_LABELS;
  readonly notValuedMessage = NOT_VALUED_MESSAGE;

  visible = false;
  loading = true;
  errorMessage = '';
  rows: MovementValuation[] = [];

  private modules = inject(ModulesService);
  private valuation = inject(ValuationApiService);
  private api = inject(MovementValuationApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.errorMessage = '';
    this.modules.enabledKeys$
      .pipe(
        filter((keys): keys is ReadonlySet<string> => keys !== null),
        take(1),
        map((keys) => keys.has('costing')),
        switchMap((enabled) => {
          this.visible = enabled;
          if (!enabled) {
            this.loading = false;
            return EMPTY;
          }
          return this.valuation.get();
        }),
        switchMap((valuation) => {
          this.visible = valuation.status === 'adopted';
          if (!this.visible) {
            this.loading = false;
            return EMPTY;
          }
          return this.api.list({
            sourceType: this.sourceType || undefined,
            sourceId: this.sourceId || undefined,
            movementId: this.movementId || undefined,
            pageSize: 100,
          });
        }),
        catchError((err: Error) => {
          this.loading = false;
          this.errorMessage = err.message;
          return EMPTY;
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.loading = false;
      });
  }
}
