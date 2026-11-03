import { TranslatePipe } from '@ngx-translate/core';
import { AfterViewInit, Component, DestroyRef, ElementRef, OnInit, ViewChild, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { DatatableComponent, NgxDatatableModule } from '@swimlane/ngx-datatable';
import { EMPTY, Subject, catchError, debounceTime, distinctUntilChanged, finalize, switchMap } from 'rxjs';
import { Profile, ProfileKind } from '../models/profile';
import { PersonnelApiService, profileError } from '../services/personnel-api.service';
import { confirmProfileState } from '../services/profile-confirmation';

@Component({
  selector: 'app-personnel-list', templateUrl: './profile-list.component.html',
  styleUrl: './profile-list.component.scss',
  imports: [TranslatePipe, RouterLink, ReactiveFormsModule, NgxDatatableModule],
})
export class ProfileListComponent implements OnInit, AfterViewInit {
  private route = inject(ActivatedRoute);
  private api = inject(PersonnelApiService);
  private destroyRef = inject(DestroyRef);
  readonly kind = this.route.snapshot.data['kind'] as ProfileKind;
  readonly title = this.kind === 'professionals' ? 'Profesionales' : 'Especialidades';
  readonly base = `/pocketbiz/personnel/${this.kind}`;
  readonly search = new FormControl('', { nonNullable: true });
  readonly status = new FormControl('true', { nonNullable: true });
  readonly specialty = new FormControl('', { nonNullable: true });
  readonly messages = { emptyMessage: 'No hay registros que coincidan.', totalMessage: 'en total' };
  private reload$ = new Subject<void>();
  rows: Profile[] = [];
  specialties: Profile[] = [];
  total = 0;
  pageIndex = 0;
  loading = false;
  error = '';
  message = '';
  saving = false;
  @ViewChild(DatatableComponent) table?: DatatableComponent;
  @ViewChild('tableContainer') tableContainer?: ElementRef<HTMLElement>;

  ngAfterViewInit(): void {
    // El sidebar anima su ancho después de window.resize. Recalcular con el ancho real
    // evita que ngx-datatable conserve un viewport casi nulo al cambiar de breakpoint.
    let lastWidth = 0;
    const observer = new ResizeObserver(entries => {
      const width = entries[0]?.contentRect.width || 0;
      if (width > 0 && width !== lastWidth) { lastWidth = width; this.table?.recalculate(); }
    });
    if (this.tableContainer) observer.observe(this.tableContainer.nativeElement);
    this.destroyRef.onDestroy(() => observer.disconnect());
  }

  ngOnInit(): void {
    this.reload$.pipe(switchMap(() => {
      this.loading = true;
      this.error = '';
      const params: Record<string, string | number> = { search: this.search.value, page: this.pageIndex + 1, page_size: 10 };
      if (this.status.value) params['active'] = this.status.value;
      if (this.specialty.value) params['specialty_id'] = this.specialty.value;
      return this.api.list(this.kind, params).pipe(
        catchError(error => { this.error = profileError(error); this.rows = []; this.total = 0; return EMPTY; }),
        finalize(() => this.loading = false),
      );
    }), takeUntilDestroyed(this.destroyRef)).subscribe(page => { this.rows = page.results; this.total = page.count; });
    this.search.valueChanges.pipe(debounceTime(300), distinctUntilChanged(), takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refresh());
    this.status.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refresh());
    this.specialty.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => this.refresh());
    if (this.kind === 'professionals') this.api.specialties().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: rows => this.specialties = rows, error: error => this.error = profileError(error),
    });
    this.refresh();
  }
  refresh(): void { this.pageIndex = 0; this.reload$.next(); }
  onPage(event: { offset: number }): void {
    if (this.pageIndex !== event.offset) { this.pageIndex = event.offset; this.reload$.next(); }
  }
  names(row: Profile): string { return row.specialties?.map(item => item.name).join(', ') || 'Sin especialidades'; }
  async toggle(item: Profile): Promise<void> {
    if (this.saving) return;
    this.saving = true;
    if (!await confirmProfileState(item)) { this.saving = false; return; }
    this.api.setActive(this.kind, item).pipe(finalize(() => this.saving = false), takeUntilDestroyed(this.destroyRef)).subscribe({
      next: () => { this.message = 'Estado actualizado.'; this.refresh(); },
      error: error => this.error = profileError(error),
    });
  }
}
