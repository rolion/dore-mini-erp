import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import { RecipeToggleComponent } from '../../components/recipe-toggle.component';
import { Recipe, RecipeApiError, formatQuantity } from '../../models/recipe';
import { RecipesApiService } from '../../services/recipes-api.service';

@Component({
  selector: 'app-recipe-detail',
  imports: [TranslatePipe, RouterLink, DatePipe, RecipeToggleComponent],
  templateUrl: './recipe-detail.component.html',
})
export class RecipeDetailComponent implements OnInit {
  private api = inject(RecipesApiService);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  recipe: Recipe | null = null;
  loading = true;
  error = '';
  readonly quantity = formatQuantity;

  ngOnInit(): void { this.load(); }

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
