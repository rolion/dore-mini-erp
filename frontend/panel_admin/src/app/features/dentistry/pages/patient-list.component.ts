import { tr } from '../../../core/i18n/translate';
import { TranslatePipe } from '@ngx-translate/core';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { PatientCreateComponent } from './patient-create.component';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, catchError, debounceTime, finalize, merge, switchMap, tap } from 'rxjs';
import { PatientSummary } from '../models/patient';
import { DentistryApiService, errorMessage } from '../services/dentistry-api.service';

@Component({
  selector: 'app-patient-list', imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgxDatatableModule],
  templateUrl: './patient-list.component.html',
})
export class PatientListComponent implements OnInit {
  private modal = inject(NgbModal);
  private api = inject(DentistryApiService);
  private route = inject(ActivatedRoute);
  private router = inject(Router);
  private destroyRef = inject(DestroyRef);
  search = new FormControl('', { nonNullable: true });
  active = new FormControl('true', { nonNullable: true });
  rows: PatientSummary[] = [];
  count = 0;
  page = 1;
  loading = false;
  error = '';
  messages = { emptyMessage: tr('DENTISTRY.PATIENT_LIST.NO_HAY_PACIENTES_QUE_COINCIDAN'), totalMessage: tr('COMMON.IN_TOTAL') };
  ngOnInit() {
    merge(this.search.valueChanges.pipe(debounceTime(300)), this.active.valueChanges)
      .pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.filter());
    this.route.queryParamMap.pipe(
      tap(params => {
        this.search.setValue(params.get('search') ?? '', { emitEvent: false });
        const active = params.get('active') ?? 'true';
        this.active.setValue(['true', 'false', ''].includes(active) ? active : 'true', { emitEvent: false });
        this.page = Math.max(1, Number(params.get('page')) || 1);
        if (params.get('new') === 'true') {
          void this.router.navigate([], { relativeTo: this.route, queryParams: { new: null }, queryParamsHandling: 'merge', replaceUrl: true });
          this.openCreate();
        }
      }),
      switchMap(() => {
        this.loading = true; this.error = ''; this.rows = [];
        return this.api.list(this.search.value, this.active.value, this.page).pipe(
          catchError((error: HttpErrorResponse) => { this.error = errorMessage(error); this.count = 0; return EMPTY; }),
          finalize(() => this.loading = false));
      }), takeUntilDestroyed(this.destroyRef),
    ).subscribe(result => { this.rows = result.results; this.count = result.count; });
  }
  openCreate() {
    const ref = this.modal.open(PatientCreateComponent, { size: 'lg', centered: true, scrollable: true,
      backdrop: 'static', keyboard: false, ariaLabelledBy: 'new-patient-title' });
    ref.componentInstance.backFilters = this.filters;
  }
  get filters() { return { search: this.search.value, active: this.active.value, page: this.page }; }
  filter(page = 1) {
    this.router.navigate([], { relativeTo: this.route, queryParams: { search: this.search.value, active: this.active.value, page } });
  }
  clear() { this.search.setValue('', { emitEvent: false }); this.active.setValue('true', { emitEvent: false }); this.filter(); }
  retry() {
    this.loading = true; this.error = '';
    this.api.list(this.search.value, this.active.value, this.page).pipe(
      finalize(() => this.loading = false), takeUntilDestroyed(this.destroyRef),
    ).subscribe({ next: result => { this.rows = result.results; this.count = result.count; },
      error: (error: HttpErrorResponse) => this.error = errorMessage(error) });
  }
}
