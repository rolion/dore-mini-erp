import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { AbstractControl, FormArray, FormControl, FormGroup, ReactiveFormsModule, ValidationErrors, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgSelectModule } from '@ng-select/ng-select';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, Subject, catchError, debounceTime, distinctUntilChanged, finalize, map, merge, of, switchMap, tap } from 'rxjs';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { ProductsApiService } from '../../../products/services/products-api.service';
import { Recipe, RecipeApiError, RecipeFieldErrors, RecipeInput, RecipeLineErrors, formatQuantity } from '../../models/recipe';
import { RecipesApiService } from '../../services/recipes-api.service';

export interface ProductOption {
  id: string;
  name: string;
  unitId: string | null;
  unitAbbreviation: string | null;
}

type IngredientGroup = FormGroup<{ product: FormControl<ProductOption | null>; quantity: FormControl<string> }>;

const DECIMAL = /^\d+(\.\d{1,4})?$/;

/** Cantidad positiva con hasta 4 decimales (el servidor revalida, también las fracciones según la unidad). */
export function positiveQuantity(control: AbstractControl): ValidationErrors | null {
  const value = String(control.value ?? '').trim();
  if (!value) return { required: true };
  if (!DECIMAL.test(value)) return { decimal: true };
  return Number(value) > 0 ? null : { positive: true };
}

@Component({
  selector: 'app-recipe-form',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgSelectModule],
  templateUrl: './recipe-form.component.html',
})
export class RecipeFormComponent implements OnInit, HasUnsavedChanges {
  private api = inject(RecipesApiService);
  private products = inject(ProductsApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);

  readonly recipeId = this.route.snapshot.paramMap.get('id');
  readonly form = new FormGroup({
    name: new FormControl('', { nonNullable: true, validators: [Validators.required, Validators.maxLength(150)] }),
    result: new FormControl<ProductOption | null>(null, Validators.required),
    yieldQuantity: new FormControl('', { nonNullable: true, validators: [positiveQuantity] }),
    ingredients: new FormArray<IngredientGroup>([]),
  });
  productOptions: ProductOption[] = [];
  productsLoading = false;
  readonly productInput$ = new Subject<string>();
  loading = !!this.recipeId;
  saving = false;
  submitted = false;
  error = '';
  server: RecipeFieldErrors = { lines: {} };
  readonly quantity = formatQuantity;

  get lines(): FormArray<IngredientGroup> { return this.form.controls.ingredients; }
  get result(): ProductOption | null { return this.form.controls.result.value; }

  ngOnInit(): void {
    merge(of(''), this.productInput$.pipe(debounceTime(300), distinctUntilChanged())).pipe(
      tap(() => this.productsLoading = true),
      switchMap(term => this.searchProducts(term)),
      takeUntilDestroyed(this.destroyRef),
    ).subscribe(options => { this.productOptions = options; this.productsLoading = false; });
    if (this.recipeId) {
      this.api.get(this.recipeId).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
        next: recipe => this.patch(recipe),
        error: (error: RecipeApiError) => this.error = error.message,
      });
    } else {
      this.addLine();
      this.form.markAsPristine();
    }
  }

  private searchProducts(term: string): Observable<ProductOption[]> {
    return this.products.list({ search: term.trim(), active: true, page: 1, pageSize: 20 }).pipe(
      map(page => page.results.map(product => ({
        id: product.id, name: product.name, unitId: product.baseUnit?.id ?? null,
        unitAbbreviation: product.baseUnit?.abbreviation ?? null,
      }))),
      catchError(() => of([] as ProductOption[])));
  }

  private patch(recipe: Recipe): void {
    this.form.controls.name.setValue(recipe.name);
    this.form.controls.result.setValue({
      id: recipe.resultProduct.id, name: recipe.resultProduct.name ?? '', unitId: recipe.resultProduct.unit?.id ?? null,
      unitAbbreviation: recipe.resultProduct.unit?.abbreviation ?? null,
    });
    this.form.controls.yieldQuantity.setValue(formatQuantity(recipe.yieldQuantity));
    this.lines.clear();
    for (const line of recipe.ingredients) {
      this.addLine({ id: line.productId, name: line.productName ?? '', unitId: line.unitId, unitAbbreviation: line.unitAbbreviation },
        formatQuantity(line.quantity));
    }
    this.form.markAsPristine();
  }

  addLine(product: ProductOption | null = null, quantity = ''): void {
    this.lines.push(new FormGroup({
      product: new FormControl<ProductOption | null>(product, Validators.required),
      quantity: new FormControl(quantity, { nonNullable: true, validators: [positiveQuantity] }),
    }));
    this.form.markAsDirty();
  }

  removeLine(index: number): void {
    this.lines.removeAt(index);
    this.server = { ...this.server, lines: {} };
    this.form.markAsDirty();
  }

  sameProduct = (a: ProductOption, b: ProductOption): boolean => a.id === b.id;

  isDuplicate(index: number): boolean {
    const id = this.lines.at(index).controls.product.value?.id;
    return !!id && this.lines.controls.some((line, other) => other !== index && line.controls.product.value?.id === id);
  }

  lineErrors(index: number): RecipeLineErrors { return this.server.lines[index] ?? {}; }

  hasUnsavedChanges(): boolean { return this.form.dirty && !this.saving; }

  @HostListener('window:beforeunload', ['$event'])
  beforeUnload(event: BeforeUnloadEvent): void {
    if (this.hasUnsavedChanges()) { event.preventDefault(); event.returnValue = ''; }
  }

  private get hasLocalProblems(): boolean {
    return this.form.invalid || this.lines.length === 0 || this.lines.controls.some((_, index) => this.isDuplicate(index))
      || this.lines.controls.some(line => line.controls.product.value?.id === this.result?.id);
  }

  save(): void {
    this.submitted = true;
    this.error = '';
    this.server = { lines: {} };
    this.form.markAllAsTouched();
    if (this.saving || this.hasLocalProblems) return;
    const value = this.form.getRawValue();
    const input: RecipeInput = {
      name: value.name,
      resultProductId: value.result?.id ?? '',
      yieldQuantity: value.yieldQuantity,
      ingredients: this.lines.controls.map(line => ({
        productId: line.controls.product.value?.id ?? '',
        unitId: line.controls.product.value?.unitId ?? null,
        quantity: line.controls.quantity.value,
      })),
    };
    this.saving = true;
    const request = this.recipeId ? this.api.update(this.recipeId, input) : this.api.create(input);
    request.pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: recipe => {
        this.form.markAsPristine();
        void this.router.navigate(['/pocketbiz/production/recipes', recipe.id]);
      },
      error: (error: RecipeApiError) => { this.error = error.message; this.server = error.fields; },
    });
  }

  cancel(): void {
    void this.router.navigate(this.recipeId ? ['/pocketbiz/production/recipes', this.recipeId] : ['/pocketbiz/production/recipes']);
  }
}
