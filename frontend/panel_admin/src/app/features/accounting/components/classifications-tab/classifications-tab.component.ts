import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { ToastrService } from 'ngx-toastr';
import { EMPTY, Subject, catchError, finalize, switchMap } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { AccountingApiError, Classification, Direction } from '../../models/accounting';
import { AccountingApiService } from '../../services/accounting-api.service';
import { ClassificationDialogComponent } from '../classification-dialog/classification-dialog.component';

export type StatusFilter = 'all' | 'active' | 'inactive';
export type DirectionFilter = 'all' | Direction;

/** Pestaña «Clasificaciones»: listado con filtros de estado (activas) y dirección, alta/edición en diálogo. */
@Component({
  selector: 'app-classifications-tab',
  templateUrl: './classifications-tab.component.html',
  styleUrl: './classifications-tab.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule],
})
export class ClassificationsTabComponent implements OnInit {
  readonly statusControl = new FormControl<StatusFilter>('active', { nonNullable: true });
  readonly directionControl = new FormControl<DirectionFilter>('all', { nonNullable: true });

  rows: Classification[] = [];
  loading = false;
  errorMessage = '';

  private api = inject(AccountingApiService);
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
          return this.api.listClassifications({ active: this.activeFilter(), direction: this.directionFilter() }).pipe(
            catchError((err: AccountingApiError) => {
              this.errorMessage = err.message;
              this.rows = [];
              return EMPTY;
            }),
            finalize(() => (this.loading = false)),
          );
        }),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe((rows) => (this.rows = rows));
    this.statusControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.reload$.next());
    this.directionControl.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.reload$.next());
    this.reload$.next();
  }

  reload(): void {
    this.reload$.next();
  }

  openDialog(classification?: Classification): void {
    const ref = this.modal.open(ClassificationDialogComponent, { centered: true });
    const dialog = ref.componentInstance as ClassificationDialogComponent;
    if (classification) {
      dialog.edit(classification);
    }
    ref.result.then(
      () => this.reload$.next(),
      () => undefined, // cancelado: no hay nada que recargar
    );
  }

  /** Activar y desactivar son directos: el historial no se altera. */
  toggleActive(classification: Classification): void {
    const request = classification.isActive ? this.api.deactivateClassification(classification.id) : this.api.activateClassification(classification.id);
    request.pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (updated) => {
        this.toastr.success(updated.isActive ? tr('ACCOUNTING.CLASSIFICATIONS.CLASIFICACION_ACTIVADA') : tr('ACCOUNTING.CLASSIFICATIONS.CLASIFICACION_DESACTIVADA'));
        this.reload$.next();
      },
      error: (err: AccountingApiError) => this.toastr.error(err.message),
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

  private directionFilter(): Direction | undefined {
    const value = this.directionControl.value;
    return value === 'all' ? undefined : value;
  }
}
