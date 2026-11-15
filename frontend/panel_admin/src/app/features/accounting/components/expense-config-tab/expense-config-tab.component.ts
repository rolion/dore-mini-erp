import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { Observable, catchError, forkJoin, of } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { Classification } from '../../models/accounting';
import { CategoryConfig, ClassificationRef, ConfigStatus, ExpenseConfigError, configStatus } from '../../models/expense-config';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ExpenseConfigApiService } from '../../services/expense-config-api.service';

/** Fila de configuración: una categoría de Gastos o los pagos a proveedores (`id` nulo). */
export interface ConfigRow {
  id: string | null;
  label: string;
  classification: ClassificationRef | null;
  saving: boolean;
  error: string;
}

/** Pestaña «Egresos»: asocia a cada categoría de Gastos y a los pagos a proveedores una clasificación de egreso. */
@Component({
  selector: 'app-expense-config-tab',
  templateUrl: './expense-config-tab.component.html',
  styleUrl: './expense-config-tab.component.scss',
  imports: [TranslatePipe],
})
export class ExpenseConfigTabComponent implements OnInit {
  rows: ConfigRow[] = [];
  options: Classification[] = [];
  loading = false;
  errorMessage = '';
  /** Aviso cuando Gastos o Compras no están habilitados (el resto de la pestaña sigue disponible). */
  warnings: string[] = [];

  private config = inject(ExpenseConfigApiService);
  private accounting = inject(AccountingApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.errorMessage = '';
    this.warnings = [];
    forkJoin({
      options: this.accounting.listClassifications({ active: true, direction: 'EXPENSE' }),
      categories: this.optional(this.config.listCategories(), [] as CategoryConfig[]),
      payments: this.optional(this.config.getPaymentClassification(), null),
    })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ options, categories, payments }) => {
          this.options = options;
          this.rows = [this.paymentRow(payments), ...categories.map((c) => this.categoryRow(c))];
          this.loading = false;
        },
        error: (err: Error) => {
          this.errorMessage = err.message;
          this.rows = [];
          this.loading = false;
        },
      });
  }

  status(row: ConfigRow): ConfigStatus {
    return configStatus(row.classification);
  }

  /** Opciones del selector: las activas de egreso y, si la asociada ya no lo es, esa para no perder el valor mostrado. */
  optionsFor(row: ConfigRow): { id: string; name: string }[] {
    const current = row.classification;
    const extra = current && !this.options.some((o) => o.id === current.id) ? [{ id: current.id, name: current.name || tr('ACCOUNTING.EXPENSE_CONFIG.CLASIFICACION_NO_DISPONIBLE') }] : [];
    return [...this.options.map((o) => ({ id: o.id, name: o.name })), ...extra];
  }

  onChange(row: ConfigRow, value: string): void {
    const classificationId = value === '' ? null : value;
    row.saving = true;
    row.error = '';
    const request =
      row.id === null
        ? this.config.setPaymentClassification(classificationId)
        : this.config.setCategoryClassification(row.id, classificationId);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        row.classification = result;
        row.saving = false;
        this.toastr.success(tr('ACCOUNTING.EXPENSE_CONFIG.CLASIFICACION_GUARDADA'));
      },
      error: (err: ExpenseConfigError) => {
        row.error = err.message;
        row.saving = false;
      },
    });
  }

  /** Si Gastos o Compras no están habilitados (o fallan), su parte se omite con un aviso y el resto sigue. */
  private optional<T>(source: Observable<T>, fallback: T): Observable<T> {
    return source.pipe(
      catchError((err: Error) => {
        this.warnings.push(err.message);
        return of(fallback);
      }),
    );
  }

  private paymentRow(classification: ClassificationRef | null): ConfigRow {
    return { id: null, label: tr('ACCOUNTING.EXPENSE_CONFIG.PAGOS_A_PROVEEDORES'), classification, saving: false, error: '' };
  }

  private categoryRow(category: CategoryConfig): ConfigRow {
    return { id: category.id, label: category.name, classification: category.classification, saving: false, error: '' };
  }
}
