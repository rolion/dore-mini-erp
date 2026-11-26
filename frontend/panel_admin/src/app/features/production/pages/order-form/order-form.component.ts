import { BreakpointObserver } from '@angular/cdk/layout';
import { Component, DestroyRef, ElementRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormControl, FormGroup, ReactiveFormsModule, ValidationErrors } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, finalize, map, merge, of, switchMap, tap } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import {
  OrderApiError, OrderFieldErrors, OrderWarehouse, ProductionOrder, formatOrderNumber, fromScaled, multiplyQuantity, parsePreparations, toScaled,
} from '../../models/order';
import { Recipe, formatQuantity } from '../../models/recipe';
import { OrdersApiService } from '../../services/orders-api.service';
import { RecipesApiService } from '../../services/recipes-api.service';

/** Por debajo de 957 px los ingredientes previstos pasan a tarjetas. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

export interface PreviewLine {
  name: string;
  unit: string;
  perPreparation: string;
  total: string;
}

export interface Preview {
  productName: string;
  unit: string;
  output: string;
  lines: PreviewLine[];
}

/** Receta (o su copia en la orden) sobre la que se calcula lo previsto. */
interface PreviewSource {
  productName: string;
  unit: string;
  yieldQuantity: string;
  lines: { name: string; unit: string; quantity: string }[];
}

/** Entero de 1 a 99999 (el servidor revalida). */
export function preparationsValidator(control: AbstractControl): ValidationErrors | null {
  const value = String(control.value ?? '').trim();
  if (!value) return { required: true };
  return parsePreparations(value) === null ? { preparations: true } : null;
}

@Component({
  selector: 'app-order-form',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgSelectModule],
  templateUrl: './order-form.component.html',
  styleUrl: './order-form.component.scss',
})
export class OrderFormComponent implements OnInit, HasUnsavedChanges {
  private api = inject(OrdersApiService);
  private recipes = inject(RecipesApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  private host = inject<ElementRef<HTMLElement>>(ElementRef);
  private breakpoints = inject(BreakpointObserver);
  /** Pantalla estrecha (< 957 px): tarjetas en lugar de tabla. */
  compact = false;

  readonly routeId = this.route.snapshot.paramMap.get('id');
  /** Id de la orden ya guardada (una alta que se guardó pero no pudo iniciarse sigue como edición). */
  private currentId = this.routeId;
  readonly form = new FormGroup({
    recipe: new FormControl<Recipe | null>(null),
    warehouse: new FormControl<OrderWarehouse | null>(null),
    preparations: new FormControl('', { nonNullable: true, validators: [preparationsValidator] }),
  });
  /** Orden en edición: la receta es solo lectura (su copia). */
  order: ProductionOrder | null = null;
  recipeOptions: Recipe[] = [];
  recipesLoading = false;
  recipesChecked = false;
  readonly recipeInput$ = new Subject<string>();
  warehouses: OrderWarehouse[] = [];
  warehousesChecked = false;
  loading = !!this.routeId;
  saving = false;
  submitted = false;
  error = '';
  server: OrderFieldErrors = {};
  readonly quantity = formatQuantity;
  readonly number = formatOrderNumber;

  get isEdit(): boolean { return !!this.routeId; }
  get noRecipes(): boolean { return !this.isEdit && this.recipesChecked && this.recipeOptions.length === 0 && !this.recipeSearched; }
  get noWarehouses(): boolean { return this.warehousesChecked && this.warehouses.length === 0; }
  private recipeSearched = false;
  get blocked(): boolean { return this.noRecipes || this.noWarehouses; }

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    this.api.warehouses().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: items => {
        this.warehouses = items;
        this.warehousesChecked = true;
        if (!this.isEdit && !this.form.controls.warehouse.value) {
          const preferred = items.find(item => item.isDefault) ?? (items.length === 1 ? items[0] : null);
          if (preferred) { this.form.controls.warehouse.setValue(preferred); this.form.markAsPristine(); }
        }
        this.syncWarehouse();
      },
      error: (error: OrderApiError) => { this.error = error.message; },
    });
    if (this.isEdit) {
      this.api.get(this.routeId ?? '').pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
        next: order => this.patch(order),
        error: (error: OrderApiError) => this.error = error.message,
      });
    } else {
      merge(of(''), this.recipeInput$.pipe(debounceTime(300), distinctUntilChanged())).pipe(
        tap(() => this.recipesLoading = true),
        switchMap(term => this.searchRecipes(term)),
        takeUntilDestroyed(this.destroyRef),
      ).subscribe(options => { this.recipeOptions = options; this.recipesLoading = false; });
    }
  }

  private searchRecipes(term: string): Observable<Recipe[]> {
    const search = term.trim();
    this.recipeSearched = !!search;
    return this.recipes.list({ search, status: 'active', page: 1, pageSize: 20 }).pipe(
      map(page => page.results),
      tap(() => this.recipesChecked = true),
      catchError(() => { this.recipesChecked = true; return of([] as Recipe[]); }));
  }

  private patch(order: ProductionOrder): void {
    if (order.status !== 'draft') {
      this.error = '';
      void this.router.navigate(['/pocketbiz/production/orders', order.id]);
      return;
    }
    this.order = order;
    this.form.controls.preparations.setValue(String(order.preparations));
    this.syncWarehouse();
    this.form.markAsPristine();
  }

  /** En edición, selecciona el almacén guardado (aunque ya no esté en la lista de activos: el servidor lo rechazará). */
  private syncWarehouse(): void {
    const order = this.order;
    if (!order || this.form.controls.warehouse.value) return;
    const found = this.warehouses.find(item => item.id === order.warehouse.id)
      ?? { id: order.warehouse.id, name: order.warehouse.name, isDefault: false };
    if (!this.warehouses.some(item => item.id === found.id)) this.warehouses = [...this.warehouses, found];
    this.form.controls.warehouse.setValue(found);
    this.form.markAsPristine();
  }

  sameItem = (a: { id: string }, b: { id: string }): boolean => a.id === b.id;

  private get source(): PreviewSource | null {
    const order = this.order;
    if (order) {
      return {
        productName: order.resultProduct.name ?? '', unit: order.resultProduct.unit?.abbreviation ?? '',
        yieldQuantity: order.yieldPerPreparation,
        lines: order.ingredients.map(line => ({
          name: line.productName ?? '', unit: line.unitAbbreviation ?? '', quantity: line.quantityPerPreparation,
        })),
      };
    }
    const recipe = this.form.controls.recipe.value;
    if (!recipe) return null;
    return {
      productName: recipe.resultProduct.name ?? '', unit: recipe.resultProduct.unit?.abbreviation ?? '',
      yieldQuantity: recipe.yieldQuantity,
      lines: recipe.ingredients.map(line => ({ name: line.productName ?? '', unit: line.unitAbbreviation ?? '', quantity: line.quantity })),
    };
  }

  /** Lo previsto en vivo: cantidades × preparaciones con aritmética entera (sin `float`). */
  get preview(): Preview | null {
    const source = this.source;
    const preparations = parsePreparations(this.form.controls.preparations.value);
    if (!source || preparations === null) return null;
    const output = multiplyQuantity(source.yieldQuantity, preparations);
    if (output === null) return null;
    const lines: PreviewLine[] = [];
    for (const line of source.lines) {
      const total = multiplyQuantity(line.quantity, preparations);
      if (total === null) return null;
      lines.push({ name: line.name, unit: line.unit, perPreparation: fromScaled(toScaled(line.quantity) ?? 0n), total });
    }
    return { productName: source.productName, unit: source.unit, output, lines };
  }

  /** Recetas activas al crear; en edición la receta ya no se elige. */
  private get recipeMissing(): boolean { return !this.isEdit && !this.form.controls.recipe.value; }

  hasUnsavedChanges(): boolean { return this.form.dirty && !this.saving; }

  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(event: BeforeUnloadEvent): void {
    if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; }
  }

  saveDraft(): void { this.submit(false); }

  startPreparation(): void { this.submit(true); }

  private submit(start: boolean): void {
    this.submitted = true;
    this.error = '';
    this.server = {};
    this.form.markAllAsTouched();
    if (this.saving) return;
    if (this.blocked || this.recipeMissing || !this.form.controls.warehouse.value || this.form.controls.preparations.invalid) {
      this.focusFirstError();
      return;
    }
    this.saving = true;
    this.persist().pipe(
      switchMap(order => start ? this.api.start(order.id) : of(order)),
      finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: order => {
        this.form.markAsPristine();
        void this.router.navigate(['/pocketbiz/production/orders', order.id]);
      },
      error: (error: OrderApiError) => {
        this.error = error.message;
        this.server = error.fields;
        this.focusFirstError();
      },
    });
  }

  private persist(): Observable<ProductionOrder> {
    const value = this.form.getRawValue();
    const warehouseId = value.warehouse?.id ?? '';
    const preparations = parsePreparations(value.preparations) ?? 0;
    if (this.currentId) return this.api.update(this.currentId, { warehouseId, preparations });
    return this.api.create({ recipeId: value.recipe?.id ?? '', warehouseId, preparations }).pipe(
      tap(order => { this.currentId = order.id; this.form.markAsPristine(); }));
  }

  /** Lleva el foco al control del primer error visible (accesibilidad del formulario). */
  private focusFirstError(): void {
    setTimeout(() => {
      const message = this.host.nativeElement.querySelector('small.text-danger');
      const control = message?.parentElement?.querySelector<HTMLElement>('input, select, .ng-input input');
      (control ?? (message as HTMLElement | null))?.focus?.();
    });
  }

  cancel(): void {
    void this.router.navigate(this.routeId ? ['/pocketbiz/production/orders', this.routeId] : ['/pocketbiz/production/orders']);
  }
}
