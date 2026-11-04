import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { ProductUsesInput, productUses } from './product-uses';

/** Chips con texto de los usos de un producto (vendible, comprable, insumo) o «Sin usos». */
@Component({
  selector: 'app-product-uses',
  imports: [TranslatePipe],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    @for (use of uses(); track use) {
      @switch (use) {
        @case ('sell') {
          <span class="badge-outline col-green d-inline-block me-1">{{ 'PRODUCTS.PRODUCT_USES.VENDIBLE' | translate }}</span>
        }
        @case ('buy') {
          <span class="badge-outline col-blue d-inline-block me-1">{{ 'PRODUCTS.PRODUCT_USES.COMPRABLE' | translate }}</span>
        }
        @case ('ingredient') {
          <span class="badge-outline col-purple d-inline-block me-1" [title]="'PRODUCTS.PRODUCT_USES.INSUMO_AYUDA' | translate">{{
            'PRODUCTS.PRODUCT_USES.INSUMO' | translate
          }}</span>
        }
      }
    } @empty {
      <span class="badge-outline col-grey d-inline-block">{{ 'PRODUCTS.PRODUCT_USES.SIN_USOS' | translate }}</span>
    }
  `,
})
export class ProductUsesComponent {
  readonly product = input.required<ProductUsesInput>();
  protected readonly uses = computed(() => productUses(this.product()));
}
