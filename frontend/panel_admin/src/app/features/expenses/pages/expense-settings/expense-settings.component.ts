import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { RouterLink } from '@angular/router';
import { EMPTY, expand, reduce } from 'rxjs';
import { TranslatePipe } from '@ngx-translate/core';
import { PostingConfigPanelComponent } from '../../../accounting/components/posting-config-panel/posting-config-panel.component';
import { PostingCategory } from '../../../accounting/models/posting-config';
import { CategoriesApiService } from '../../services/categories-api.service';

const PAGE_SIZE = 100;

/** Configuración de Gastos: cuenta de gasto por categoría y cuenta de pago por método (asientos automáticos). */
@Component({
  selector: 'app-expense-settings',
  templateUrl: './expense-settings.component.html',
  imports: [TranslatePipe, RouterLink, PostingConfigPanelComponent],
})
export class ExpenseSettingsComponent implements OnInit {
  categories: PostingCategory[] | null = null;
  loadFailed = false;

  private api = inject(CategoriesApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  /** Las categorías son de Gastos: el panel de Contabilidad solo recibe su id, nombre y estado. */
  load(): void {
    this.loadFailed = false;
    this.api
      .list({ pageSize: PAGE_SIZE, page: 1 })
      .pipe(
        // Todas las páginas: una categoría sin cargar no se podría configurar y el panel diría «completa» sin ella.
        expand((page, index) => (page.next ? this.api.list({ pageSize: PAGE_SIZE, page: index + 2 }) : EMPTY)),
        reduce((all: PostingCategory[], page) => [...all, ...page.results.map((c) => ({ id: c.id, name: c.name, isActive: c.active }))], []),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (categories) => (this.categories = categories),
        error: () => (this.loadFailed = true),
      });
  }
}
