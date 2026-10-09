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
  imports: [RouterLink, NgxDatatableModule, ReactiveFormsModule],
})
export class CategoryListComponent implements OnInit {
  readonly pageSize = 10;
  readonly messages = {
    emptyMessage: 'Aún no hay categorías. Crea la primera para registrar gastos.',
    totalMessage: 'en total',
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
        this.toastr.success(updated.active ? 'Categoría activada' : 'Categoría desactivada');
        this.reload$.next();
      },
      error: (err: ExpensesApiError) => this.toastr.error(err.message),
    });
  }

  /** Confirmación previa a cambiar el estado; separada para poder sustituirla en pruebas. */
  protected async confirmToggle(category: ExpenseCategory): Promise<boolean> {
    const verb = category.active ? 'desactivar' : 'activar';
    const result = await Swal.fire({
      titleText: `¿Quieres ${verb} la categoría "${category.name}"?`,
      text: category.active
        ? 'Dejará de ofrecerse para nuevos gastos. Los gastos ya registrados la conservan.'
        : 'Volverá a ofrecerse para nuevos gastos.',
      showCancelButton: true,
      confirmButtonColor: '#8963ff',
      cancelButtonColor: '#fb7823',
      confirmButtonText: 'Sí',
      cancelButtonText: 'Cancelar',
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
