import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { NgbPagination } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { EMPTY, Subject, catchError, finalize, startWith, switchMap, throwError } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { RecipeToggleComponent } from '../../components/recipe-toggle.component';
import { Recipe, RecipeApiError, RecipeStatus, formatQuantity } from '../../models/recipe';
import { RecipeFiltersState, RecipesApiService } from '../../services/recipes-api.service';

@Component({
  selector: 'app-recipe-list',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, NgbPagination, RecipeToggleComponent],
  templateUrl: './recipe-list.component.html',
})
export class RecipeListComponent implements OnInit {
  readonly state = inject(RecipeFiltersState);
  private api = inject(RecipesApiService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();
  search = new FormControl(this.state.search, { nonNullable: true });
  status = new FormControl<RecipeStatus>(this.state.status, { nonNullable: true });
  rows: Recipe[] = [];
  total = 0;
  pageSize = 20;
  loading = false;
  error = '';
  success = '';
  readonly quantity = formatQuantity;

  ngOnInit(): void {
    this.reload$.pipe(startWith(undefined), switchMap(() => {
      this.loading = true;
      this.error = '';
      const params = { search: this.state.search, status: this.state.status, page: this.state.pageIndex + 1, pageSize: this.pageSize };
      return this.api.list(params).pipe(
        catchError((error: RecipeApiError) => {
          if (!error.invalidPage || this.state.pageIndex === 0) return throwError(() => error);
          this.state.pageIndex = 0;
          return this.api.list({ ...params, page: 1 });
        }),
        catchError((error: RecipeApiError) => { this.error = error.message; this.rows = []; this.total = 0; return EMPTY; }),
        finalize(() => this.loading = false));
    }), takeUntilDestroyed(this.destroyRef)).subscribe(page => { this.rows = page.results; this.total = page.count; });
  }

  reload(): void { this.reload$.next(); }

  onPage(page: number): void {
    if (this.loading || page - 1 === this.state.pageIndex) return;
    this.state.pageIndex = page - 1;
    this.reload();
  }

  get isDefaultFilter(): boolean { return !this.state.search && this.state.status === 'active'; }

  applyFilters(): void {
    this.state.search = this.search.value.trim();
    this.state.status = this.status.value;
    this.state.pageIndex = 0;
    this.reload();
  }

  clearFilters(): void {
    this.search.setValue('', { emitEvent: false });
    this.status.setValue('active', { emitEvent: false });
    this.applyFilters();
  }

  onUpdated(recipe: Recipe): void {
    this.success = recipe.active ? tr('PRODUCTION.RECIPES.ACTIVATED') : tr('PRODUCTION.RECIPES.DEACTIVATED');
    this.reload();
  }
}
