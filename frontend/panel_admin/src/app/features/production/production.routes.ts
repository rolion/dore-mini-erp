import { Routes } from '@angular/router';
import { unsavedChangesGuard } from '../../core/guard/unsaved-changes.guard';
import { RecipeDetailComponent } from './pages/recipe-detail/recipe-detail.component';
import { RecipeFormComponent } from './pages/recipe-form/recipe-form.component';
import { RecipeListComponent } from './pages/recipe-list/recipe-list.component';

export const RECIPES_ROUTE: Routes = [
  { path: '', component: RecipeListComponent },
  { path: 'new', component: RecipeFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id/edit', component: RecipeFormComponent, canDeactivate: [unsavedChangesGuard] },
  { path: ':id', component: RecipeDetailComponent },
];
