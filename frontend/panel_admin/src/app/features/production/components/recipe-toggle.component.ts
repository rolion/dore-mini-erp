import { Component, DestroyRef, EventEmitter, Input, Output, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { finalize } from 'rxjs';
import Swal from 'sweetalert2';
import { tr } from '../../../core/i18n/translate';
import { Recipe, RecipeApiError } from '../models/recipe';
import { RecipesApiService } from '../services/recipes-api.service';

@Component({
  selector: 'app-recipe-toggle',
  imports: [TranslatePipe],
  template: `
    <button type="button" [class]="compact ? 'btn btn-tbl-edit btn-tbl-toggle h-auto' : 'btn btn-warning'"
      [disabled]="busy" (click)="toggle()" [title]="label" [attr.aria-label]="label">
      @if (compact) { <i class="fas" [class.fa-ban]="recipe.active" [class.fa-check]="!recipe.active" aria-hidden="true"></i> }
      @else { {{ busy ? ('PRODUCTION.RECIPES.SAVING' | translate) : label }} }
    </button>
    @if (error) { <small role="alert" class="text-danger d-block">{{ error }}</small> }
  `,
})
export class RecipeToggleComponent {
  @Input({ required: true }) recipe!: Recipe;
  @Input() compact = false;
  @Output() updated = new EventEmitter<Recipe>();
  private api = inject(RecipesApiService);
  private destroyRef = inject(DestroyRef);
  busy = false;
  error = '';

  get label(): string {
    return this.recipe.active ? tr('PRODUCTION.RECIPES.DEACTIVATE') : tr('PRODUCTION.RECIPES.ACTIVATE');
  }

  async toggle(): Promise<void> {
    if (this.busy) return;
    this.busy = true;
    this.error = '';
    const result = await Swal.fire({
      title: tr('PRODUCTION.RECIPES.CONFIRM_TITLE', { action: this.label, name: this.recipe.name }),
      text: this.recipe.active ? tr('PRODUCTION.RECIPES.CONFIRM_DEACTIVATE_TEXT') : tr('PRODUCTION.RECIPES.CONFIRM_ACTIVATE_TEXT'),
      showCancelButton: true, confirmButtonText: this.label, cancelButtonText: tr('COMMON.CANCELAR'),
    });
    if (!result.isConfirmed || this.destroyRef.destroyed) { this.busy = false; return; }
    this.api.setActive(this.recipe.id, !this.recipe.active).pipe(
      finalize(() => this.busy = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({
      next: recipe => this.updated.emit(recipe),
      error: (error: RecipeApiError) => this.error = error.message,
    });
  }
}
