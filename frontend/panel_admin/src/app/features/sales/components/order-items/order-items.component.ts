import { AsyncPipe } from '@angular/common';
import { Component, DestroyRef, inject, input, output } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { NgOptionTemplateDirective, NgSelectComponent } from '@ng-select/ng-select';
import { Observable, Subject, catchError, concat, debounceTime, distinctUntilChanged, finalize, map, of, switchMap, tap } from 'rxjs';
import { Product, ProductsApiService } from '../../../products';
import { FieldErrors, Order, OrderItem } from '../../models/order';
import { MoneyPipe } from '../../pipes/money.pipe';

export const PRODUCT_SEARCH_PAGE_SIZE = 20;
export const LAST_ITEM_TOOLTIP = 'Un pedido confirmado debe tener al menos un producto';

export interface AddItemEvent {
  productId: string;
  quantity: number;
}

export interface QuantityChangeEvent {
  item: OrderItem;
  quantity: number;
}

/**
 * Productos del pedido. Solo emite lo que el usuario pide; el servidor valida y devuelve los importes
 * (el navegador no calcula subtotales).
 */
@Component({
  selector: 'app-order-items',
  templateUrl: './order-items.component.html',
  imports: [ReactiveFormsModule, AsyncPipe, NgSelectComponent, NgOptionTemplateDirective, MoneyPipe],
})
export class OrderItemsComponent {
  readonly order = input.required<Order>();
  readonly busy = input(false);
  readonly errors = input<FieldErrors>({});
  readonly itemAdd = output<AddItemEvent>();
  readonly quantityChange = output<QuantityChangeEvent>();
  readonly itemRemove = output<OrderItem>();

  readonly lastItemTooltip = LAST_ITEM_TOOLTIP;
  readonly addForm = inject(FormBuilder).group({
    product: [null as Product | null, Validators.required],
    quantity: [1, [Validators.required, Validators.min(1)]],
  });
  readonly productInput$ = new Subject<string>();
  productsLoading = false;
  readonly products$: Observable<Product[]>;

  private api = inject(ProductsApiService);
  private destroyRef = inject(DestroyRef);

  constructor() {
    // Lista inicial de productos activos y, luego, búsqueda remota mientras se escribe.
    this.products$ = concat(
      this.searchProducts(''),
      this.productInput$.pipe(
        debounceTime(300),
        distinctUntilChanged(),
        tap(() => (this.productsLoading = true)),
        switchMap((term) => this.searchProducts(term)),
      ),
    );
    this.destroyRef.onDestroy(() => this.productInput$.complete());
  }

  /** Quitar el último ítem de un pedido ya confirmado está prohibido; el servidor lo valida igualmente. */
  isLastConfirmedItem(order: Order): boolean {
    return order.status !== 'NEW' && order.items.length === 1;
  }

  add(): void {
    const { product, quantity } = this.addForm.getRawValue();
    if (this.addForm.invalid || !product || this.busy()) {
      this.addForm.markAllAsTouched();
      return;
    }
    this.itemAdd.emit({ productId: product.id, quantity: Number(quantity) });
    this.addForm.reset({ product: null, quantity: 1 });
  }

  onQuantity(item: OrderItem, input: HTMLInputElement): void {
    const quantity = Number(input.value);
    if (!Number.isInteger(quantity) || quantity < 1) {
      input.value = String(item.quantity);
      return;
    }
    if (quantity !== item.quantity && !this.busy()) {
      this.quantityChange.emit({ item, quantity });
    }
  }

  private searchProducts(term: string): Observable<Product[]> {
    return this.api.list({ search: term.trim(), active: true, pageSize: PRODUCT_SEARCH_PAGE_SIZE }).pipe(
      map((page) => page.results),
      catchError(() => of([] as Product[])),
      finalize(() => (this.productsLoading = false)),
    );
  }
}
