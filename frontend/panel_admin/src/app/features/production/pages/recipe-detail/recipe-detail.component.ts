import { BreakpointObserver } from '@angular/cdk/layout';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { RecipeToggleComponent } from '../../components/recipe-toggle.component';
import { Recipe, RecipeApiError, formatQuantity } from '../../models/recipe';
import { RecipesApiService } from '../../services/recipes-api.service';

/** Por debajo de 957 px el detalle pasa a filas «etiqueta | valor» y a tarjetas de ingredientes. */
export const COMPACT_QUERY = '(max-width: 956.98px)';

@Component({
  selector: 'app-recipe-detail',
  imports: [TranslatePipe, RouterLink, DatePipe, RecipeToggleComponent],
  templateUrl: './recipe-detail.component.html',
  styleUrl: './recipe-detail.component.scss',
})
export class RecipeDetailComponent implements OnInit {
  private api = inject(RecipesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private breakpoints = inject(BreakpointObserver);
  /** Pantalla estrecha (< 957 px). */
  compact = false;
  recipe: Recipe | null = null;
  loading = true;
  error = '';
  readonly quantity = formatQuantity;

  ngOnInit(): void {
    this.breakpoints.observe(COMPACT_QUERY).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(state => this.compact = state.matches);
    this.load();
  }

  load(): void {
    const id = this.route.snapshot.paramMap.get('id') ?? '';
    this.loading = true;
    this.error = '';
    this.api.get(id).pipe(finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: recipe => this.recipe = recipe,
      error: (error: RecipeApiError) => this.error = error.message,
    });
  }

  /** Producto inactivo o sin unidad base: la receta no podrá guardarse hasta corregirlo. */
  get hasProductWarning(): boolean {
    const recipe = this.recipe;
    if (!recipe) return false;
    return !recipe.resultProduct.active || !recipe.resultProduct.unit
      || recipe.ingredients.some(line => !line.productActive || !line.unitAbbreviation);
  }

  onUpdated(recipe: Recipe): void { this.recipe = recipe; }
}
