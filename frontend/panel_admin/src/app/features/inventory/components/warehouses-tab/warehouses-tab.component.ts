import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { Warehouse } from '../../models/warehouse';
import { WarehousesApiService } from '../../services/warehouses-api.service';
import { WarehouseDialogComponent } from '../warehouse-dialog/warehouse-dialog.component';

export type StatusFilter = 'all' | 'active' | 'inactive';

/** Pestaña «Almacenes»: listado con búsqueda y filtro de estado (inicialmente activos) y alta/edición en diálogo. */
@Component({
  selector: 'app-warehouses-tab',
  templateUrl: './warehouses-tab.component.html',
  styleUrl: './warehouses-tab.component.scss',
  imports: [ReactiveFormsModule],
})
export class WarehousesTabComponent implements OnInit {
  readonly pageSize = 100;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

  rows: Warehouse[] = [];
  loading = false;
  errorMessage = '';
  /** Motivo de un bloqueo del servidor (saldo, recepciones pendientes, predeterminado), visible sobre la tabla. */
  blockReason = '';

  private api = inject(WarehousesApiService);
  private modal = inject(NgbModal);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);
  private reload$ = new Subject<void>();

  ngOnInit(): void {
    this.reload$
      .pipe(
        switchMap(() => {
          this.loading = true;
          this.errorMessage = '';
          return this.api
            .list({ search: this.searchControl.value.trim(), active: this.activeFilter(), pageSize: this.pageSize })
            .pipe(
              catchError((err: InventoryApiError) => {
                this.errorMessage = err.message;
                this.rows = [];
                return EMPTY;
              }),
              finalize(() => (this.loading = false)),
            );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((page) => (this.rows = page.results));

    this.searchControl.valueChanges
      .pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef))
      .subscribe(() => this.reload$.next());
    this.statusControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.reload$.next());
    this.reload$.next();
  }

  reload(): void {
    this.reload$.next();
  }

  openDialog(warehouse?: Warehouse): void {
    const ref = this.modal.open(WarehouseDialogComponent, { centered: true });
    const dialog = ref.componentInstance as WarehouseDialogComponent;
    if (warehouse) {
      dialog.edit(warehouse);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado: no hay nada que recargar
    );
  }

  toggleActive(warehouse: Warehouse): void {
    this.run(warehouse.active ? this.api.deactivate(warehouse.id) : this.api.activate(warehouse.id), (updated) =>
      updated.active ? 'Almacén activado' : 'Almacén desactivado',
    );
  }

  makeDefault(warehouse: Warehouse): void {
    this.run(this.api.makeDefault(warehouse.id), () => 'Almacén predeterminado actualizado');
  }

  private run(request: ReturnType<WarehousesApiService['activate']>, message: (w: Warehouse) => string): void {
    this.blockReason = '';
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(message(updated));
        this.reload$.next();
      },
      error: (err: InventoryApiError) => {
        if (err.status === 409) {
          this.blockReason = err.message;
        } else {
          this.toastr.error(err.message);
        }
      },
    });
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
