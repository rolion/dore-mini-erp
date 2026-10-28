import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import { InventoryApiError } from '../../models/api-error';
import { Unit } from '../../models/unit';
import { UnitsApiService } from '../../services/units-api.service';
import { UnitDialogComponent } from '../unit-dialog/unit-dialog.component';

export type StatusFilter = 'all' | 'active' | 'inactive';

/** Pestaña «Unidades»: listado con búsqueda y filtro de estado (inicialmente activas) y alta/edición en diálogo. */
@Component({
  selector: 'app-units-tab',
  templateUrl: './units-tab.component.html',
  styleUrl: './units-tab.component.scss',
  imports: [ReactiveFormsModule],
})
export class UnitsTabComponent implements OnInit {
  readonly pageSize = 100;
  readonly searchControl = new FormControl('', { nonNullable: true });
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });

  rows: Unit[] = [];
  loading = false;
  errorMessage = '';

  private api = inject(UnitsApiService);
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

  openDialog(unit?: Unit): void {
    const ref = this.modal.open(UnitDialogComponent, { centered: true });
    const dialog = ref.componentInstance as UnitDialogComponent;
    if (unit) {
      dialog.edit(unit);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado: no hay nada que recargar
    );
  }

  toggleActive(unit: Unit): void {
    const request = unit.active ? this.api.deactivate(unit.id) : this.api.activate(unit.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.active ? 'Unidad activada' : 'Unidad desactivada');
        this.reload$.next();
      },
      error: (err: InventoryApiError) => this.toastr.error(err.message),
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
