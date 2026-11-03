import { tr } from '../../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import Swal from 'sweetalert2';
import { CategoryDialogComponent } from '../../components/category-dialog/category-dialog.component';
import { ExpensesApiError } from '../../models/api-error';
import { ExpenseCategory } from '../../models/category';
import { CategoriesApiService } from '../../services/categories-api.service';

export type CategoryStatusFilter = 'all' | 'active' | 'inactive';

@Component({
  selector: 'app-category-list',
  templateUrl: './category-list.component.html',
  styleUrl: './category-list.component.scss',
  imports: [TranslatePipe, RouterLink, NgxDatatableModule, ReactiveFormsModule],
})
export class CategoryListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = {
    emptyMessage: tr('EXPENSES.CATEGORY_LIST.AUN_NO_HAY_CATEGORIAS_CREA'),
    totalMessage: tr('COMMON.IN_TOTAL'),
  };
  /** Las categorías inactivas no aparecen por defecto. */
  readonly statusControl = new FormControl<CategoryStatusFilter>('active', { nonNullable: true });

  rows: ExpenseCategory[] = [];
  total = 0;
  /** Página actual base 0, como espera ngx-datatable. */
  pageIndex = 0;
  loading = false;

  private api = inject(CategoriesApiService);
  private modal = inject(NgbModal);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          return this.api.list({ active: this.activeFilter(), page: this.pageIndex + 1, pageSize: this.pageSize }).pipe(
            catchError((err: ExpensesApiError) => {
              this.toastr.error(err.message);
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => {
        this.rows = page.results;
        this.total = page.count;
      });

    this.statusControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      this.pageIndex = 0;
      this.reload$.next();
    });

    this.reload$.next();
  }

  onPage(event: { offset: number }): void {
    if (event.offset === this.pageIndex) {
      return;
    }
    this.pageIndex = event.offset;
    this.reload$.next();
  }

  /** Abre el diálogo para crear (sin argumento) o editar una categoría; al guardar recarga la lista. */
  openDialog(category?: ExpenseCategory): void {
    const ref = this.modal.open(CategoryDialogComponent, { centered: true });
    const dialog = ref.componentInstance as CategoryDialogComponent;
    if (category) {
      dialog.edit(category);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado: no hay nada que recargar
    );
  }

  async toggleActive(category: ExpenseCategory): Promise<void> {
    if (!(await this.confirmToggle(category))) {
      return;
    }
    const request = category.active ? this.api.deactivate(category.id) : this.api.activate(category.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? tr('EXPENSES.CATEGORY_LIST.CATEGORIA_ACTIVADA') : tr('EXPENSES.CATEGORY_LIST.CATEGORIA_DESACTIVADA'));
        this.reload$.next();
      },
      error: (err: ExpensesApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(category: ExpenseCategory): Promise<boolean> {
    const verb = category.active ? tr('COMMON.VERB_DEACTIVATE') : tr('COMMON.VERB_ACTIVATE');
    const result = await Swal.fire({
      titleText: tr('EXPENSES.CATEGORY_LIST.QUIERES_LA_CATEGORIA', { p0: verb, p1: category.name }),
      text: category.active
        ? tr('EXPENSES.CATEGORY_LIST.DEJARA_DE_OFRECERSE_PARA_NUEVOS')
        : tr('EXPENSES.CATEGORY_LIST.VOLVERA_A_OFRECERSE_PARA_NUEVOS'),
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: tr('CUSTOMERS.CUSTOMER_DETAIL.SI'),
      cancelButtonText: tr('CUSTOMERS.CUSTOMER_QUICK_CREATE.CANCELAR'),
    });
    return result.isConfirmed;
  }

  private activeFilter(): boolean | undefined {
    switch (this.statusControl.value) {
      case 'active':
        return true;
      case 'inactive':
        return false;
      default:
        return undefined;
    }
  }
}
