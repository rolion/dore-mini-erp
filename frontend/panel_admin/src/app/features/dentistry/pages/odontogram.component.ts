import { DatePipe } from '@angular/common';
import { Component, DestroyRef, ElementRef, OnInit, TemplateRef, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { NgbModal } from '@ng-bootstrap/ng-bootstrap';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, catchError, finalize, forkJoin, map, of, switchMap, tap } from 'rxjs';
import { tr } from '../../../core/i18n/translate';
import { HasUnsavedChanges } from '../../../core/guard/unsaved-changes.guard';
import { PersonnelApiService } from '../../personnel/services/personnel-api.service';
import { OdontogramChartComponent } from '../components/odontogram-chart.component';
import {
  DIAGNOSIS_MAX, Dentition, Evaluation, EvaluationInput, Finding, GeneralFinding, NOTES_MAX, OdontogramCatalog,
  OdontogramCondition, REASON_MAX, SurfaceCode,
} from '../models/odontogram';
import { Patient } from '../models/patient';
import { DentistryApiService } from '../services/dentistry-api.service';
import { localDateInput } from '../services/demographics-form';
import { OdontogramApiService, evaluationError } from '../services/odontogram-api.service';
import {
  conditionName, conditionOf, findingLabel, findingsOf, pieceDentitionName, pieceKindName, surfaceName, validSurfaces,
} from '../services/odontogram-utils';

export type SaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error';
export type OdontogramView = 'chart' | 'table';

interface TableRow { piece: number; dentition: string; surfaces: string; condition: string; abbr: string; diagnosis: string; notes: string; }

@Component({
  selector: 'app-odontogram',
  imports: [TranslatePipe, DatePipe, RouterLink, ReactiveFormsModule, OdontogramChartComponent],
  templateUrl: './odontogram.component.html',
})
export class OdontogramComponent implements OnInit, HasUnsavedChanges {
  private api = inject(OdontogramApiService);
  private patients = inject(DentistryApiService);
  private personnel = inject(PersonnelApiService);
  private route = inject(ActivatedRoute);
  private modal = inject(NgbModal);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;
  private host = inject<ElementRef<HTMLElement>>(ElementRef);

  readonly id = this.route.snapshot.paramMap.get('id') ?? '';
  /** Cuando se llega desde una atención: evaluación a abrir y cita a la que se vuelve. */
  readonly queryEvaluation = this.route.snapshot.queryParamMap.get('evaluation');
  readonly appointmentId = this.route.snapshot.queryParamMap.get('appointment');
  readonly today = localDateInput();
  readonly diagnosisMax = DIAGNOSIS_MAX;
  readonly notesMax = NOTES_MAX;
  readonly reasonMax = REASON_MAX;
  readonly dentitions: Dentition[] = ['permanent', 'temporary', 'mixed'];

  patient: Patient | null = null;
  catalog: OdontogramCatalog | null = null;
  evaluations: Evaluation[] = [];
  current: Evaluation | null = null;
  professionals: { id: string; name: string }[] = [];
  findings: Finding[] = [];
  generalFindings: GeneralFinding[] = [];
  isNew = false;
  loading = false;
  busy = false;
  error = '';
  success = '';
  saveError = '';
  state: SaveState = 'idle';
  view: OdontogramView = 'chart';
  selectedPiece: number | null = null;
  findingErrors: string[] = [];
  generalErrors: string[] = [];
  findingInvalid = { condition: false, surfaces: false, notes: false, diagnosis: false };
  generalInvalid = false;
  dirty = false;

  readonly headerForm = this.fb.group({
    dentition: ['permanent' as Dentition],
    clinical_date: [localDateInput(), Validators.required],
    professional_id: [''],
  });
  readonly findingForm = this.fb.group({
    condition: ['', Validators.required],
    surfaces: [[] as SurfaceCode[]],
    diagnosis: ['', Validators.maxLength(DIAGNOSIS_MAX)],
    notes: ['', Validators.maxLength(NOTES_MAX)],
  });
  readonly generalForm = this.fb.group({
    diagnosis: ['', [Validators.required, Validators.maxLength(DIAGNOSIS_MAX)]],
    notes: ['', Validators.maxLength(NOTES_MAX)],
  });
  readonly reasonControl = this.fb.control('', [Validators.required, Validators.maxLength(REASON_MAX)]);

  ngOnInit(): void {
    this.headerForm.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => {
      if (this.editable && !this.loading) this.markDirty();
    });
    this.load();
  }

  hasUnsavedChanges(): boolean { return this.dirty && this.editable; }

  // ----- Estado derivado -----
  get archived(): boolean { return this.patient !== null && !this.patient.active; }
  get editable(): boolean {
    if (this.archived) return false;
    return this.isNew || (this.current?.status === 'draft' && this.can('edit'));
  }
  get hasDraft(): boolean { return this.evaluations.some(evaluation => evaluation.status === 'draft'); }
  get canCreate(): boolean { return !this.archived && !this.hasDraft && !this.isNew; }
  get shownFindings(): Finding[] { return this.editable ? this.findings : (this.current?.findings ?? []); }
  get shownGeneral(): GeneralFinding[] { return this.editable ? this.generalFindings : (this.current?.general_findings ?? []); }
  get dentition(): Dentition { return this.editable ? this.headerForm.controls.dentition.value : (this.current?.dentition ?? 'permanent'); }
  get hasEvaluation(): boolean { return this.isNew || this.current !== null; }
  get selectedFindings(): Finding[] { return this.selectedPiece === null ? [] : findingsOf(this.shownFindings, this.selectedPiece); }
  get selectedCondition(): OdontogramCondition | undefined { return conditionOf(this.catalog, this.findingForm.controls.condition.value); }
  get pieceSurfaces(): SurfaceCode[] { return this.selectedPiece === null ? [] : validSurfaces(this.selectedPiece); }
  get surfacesDisabled(): boolean { return this.selectedCondition?.scope === 'whole'; }
  get pieceTitle(): string {
    const piece = this.selectedPiece ?? 0;
    return tr('DENTISTRY.ODONTOGRAM.PIEZA_TITULO', { piece, type: pieceKindName(piece), dent: pieceDentitionName(piece) });
  }
  get professionalOptions(): { id: string; name: string }[] {
    const own = this.current?.professional;
    return own && !this.professionals.some(item => item.id === own.id) ? [...this.professionals, own] : this.professionals;
  }
  get rows(): TableRow[] {
    return [...this.shownFindings].sort((a, b) => a.piece - b.piece).map(finding => ({
      piece: finding.piece, dentition: pieceDentitionName(finding.piece), surfaces: finding.surfaces.length
        ? finding.surfaces.map(code => `${code} · ${surfaceName(this.catalog, code)}`).join(', ') : tr('DENTISTRY.ODONTOGRAM.PIEZA_COMPLETA'),
      condition: conditionName(this.catalog, finding.condition),
      abbr: conditionOf(this.catalog, finding.condition)?.abbr ?? finding.condition,
      diagnosis: finding.diagnosis, notes: finding.notes,
    }));
  }
  get statusText(): string {
    const key: Record<SaveState, string> = {
      idle: 'DENTISTRY.ODONTOGRAM.ESTADO_SIN_CAMBIOS', dirty: 'DENTISTRY.ODONTOGRAM.ESTADO_CAMBIOS',
      saving: 'DENTISTRY.ODONTOGRAM.ESTADO_GUARDANDO', saved: 'DENTISTRY.ODONTOGRAM.ESTADO_GUARDADO',
      error: 'DENTISTRY.ODONTOGRAM.ESTADO_ERROR',
    };
    return tr(key[this.state]);
  }
  get confirmable(): boolean {
    return this.confirmedCount > 0 && this.headerForm.valid && (this.isNew || this.can('confirm'));
  }
  get confirmedCount(): number { return this.shownFindings.length + this.shownGeneral.length; }

  can(action: Evaluation['allowed_actions'][number]): boolean {
    return !this.archived && (this.current?.allowed_actions.includes(action) ?? false);
  }
  statusLabel(evaluation: Evaluation): string {
    return tr(evaluation.status === 'draft' ? 'DENTISTRY.ODONTOGRAM.BORRADOR' : 'DENTISTRY.ODONTOGRAM.CONFIRMADA');
  }
  optionLabel(evaluation: Evaluation): string {
    return tr('DENTISTRY.ODONTOGRAM.OPCION', {
      n: evaluation.sequence, date: this.formatDate(evaluation.clinical_date), status: this.statusLabel(evaluation), author: evaluation.author.name,
    });
  }
  /** `yyyy-MM-dd` → `dd/MM/yyyy` sin pasar por Date (evita desfases de zona horaria). */
  formatDate(iso: string): string {
    const [year, month, day] = iso.split('-');
    return year && month && day ? `${day}/${month}/${year}` : iso;
  }
  dentitionName(code: Dentition): string { return tr(`DENTISTRY.ODONTOGRAM.DENT_${code.toUpperCase()}`); }
  conditionLabel(condition: OdontogramCondition): string { return `${condition.abbr} · ${conditionName(this.catalog, condition.code)}`; }
  findingText(finding: Finding): string { return findingLabel(this.catalog, finding); }
  surfaceLabel(code: SurfaceCode): string { return `${code} · ${surfaceName(this.catalog, code)}`; }
  surfaceChecked(code: SurfaceCode): boolean { return this.findingForm.controls.surfaces.value.includes(code); }

  // ----- Carga -----
  load(): void {
    this.loading = true;
    this.error = '';
    forkJoin({
      patient: this.patients.get(this.id),
      catalog: this.api.catalog(),
      page: this.api.list(this.id),
      professionals: this.personnel.list('professionals', { page_size: 100 }).pipe(
        map(page => page.results.filter(item => item.active).map(item => ({ id: item.id, name: item.name }))),
        catchError(() => of([] as { id: string; name: string }[])),
      ),
    }).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: ({ patient, catalog, page, professionals }) => {
        this.patient = patient;
        this.catalog = catalog;
        this.professionals = professionals;
        this.evaluations = page.results;
        const start = page.results.find(item => item.id === this.queryEvaluation)
          ?? page.results.find(item => item.status === 'draft') ?? page.results[0];
        if (start) this.openEvaluation(start.id); else this.loading = false;
      },
      error: error => { this.loading = false; this.error = evaluationError(error); },
    });
  }

  private openEvaluation(id: string): void {
    this.loading = true;
    this.api.get(id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => { this.loading = false; })).subscribe({
      next: evaluation => this.applyEvaluation(evaluation),
      error: error => { this.error = evaluationError(error); },
    });
  }

  private applyEvaluation(evaluation: Evaluation): void {
    this.current = evaluation;
    this.isNew = false;
    this.findings = evaluation.findings.map(finding => ({ ...finding, surfaces: [...finding.surfaces] }));
    this.generalFindings = evaluation.general_findings.map(finding => ({ ...finding }));
    this.headerForm.reset({
      dentition: evaluation.dentition, clinical_date: evaluation.clinical_date, professional_id: evaluation.professional?.id ?? '',
    }, { emitEvent: false });
    this.dirty = false;
    this.state = 'idle';
    this.saveError = '';
    this.selectedPiece = null;
    this.resetFindingForm();
    this.syncHeader();
  }

  private syncHeader(): void {
    if (this.editable) this.headerForm.enable({ emitEvent: false });
    else this.headerForm.disable({ emitEvent: false });
  }

  private refreshList(): void {
    this.api.list(this.id).pipe(takeUntilDestroyed(this.destroyRef)).subscribe(page => { this.evaluations = page.results; });
  }

  onSelectEvaluation(id: string): void {
    if (this.current && id === this.current.id && !this.isNew) return;
    if (this.hasUnsavedChanges() && !window.confirm(tr('CORE.UNSAVED_CHANGES_GUARD.HAY_CAMBIOS_SIN_GUARDAR_SALIR'))) return;
    this.success = '';
    this.openEvaluation(id);
  }

  goTo(id: string | null): void { if (id) this.onSelectEvaluation(id); }

  startNew(): void {
    this.isNew = true;
    this.current = null;
    this.findings = [];
    this.generalFindings = [];
    this.headerForm.reset({ dentition: 'permanent', clinical_date: this.today, professional_id: '' }, { emitEvent: false });
    this.dirty = false;
    this.state = 'idle';
    this.selectedPiece = null;
    this.success = '';
    this.saveError = '';
    this.syncHeader();
  }

  private focusFirst(ids: string[]): void {
    const id = ids[0];
    if (!id) return;
    queueMicrotask(() => this.host.nativeElement.querySelector<HTMLElement>(`#${id}`)?.focus());
  }

  onTabKey(event: KeyboardEvent): void {
    const views: OdontogramView[] = ['chart', 'table'];
    const index = views.indexOf(this.view);
    let next = -1;
    if (event.key === 'ArrowRight') next = (index + 1) % views.length;
    else if (event.key === 'ArrowLeft') next = (index + views.length - 1) % views.length;
    else if (event.key === 'Home') next = 0;
    else if (event.key === 'End') next = views.length - 1;
    if (next < 0) return;
    event.preventDefault();
    this.view = views[next];
    queueMicrotask(() => this.host.nativeElement.querySelector<HTMLElement>(`#odo-tab-${this.view}`)?.focus());
  }

  // ----- Edición local -----
  private markDirty(): void {
    this.dirty = true;
    if (this.state !== 'saving') this.state = 'dirty';
  }

  selectPiece(piece: number): void {
    this.selectedPiece = piece;
    this.resetFindingForm();
  }

  private resetFindingForm(): void {
    this.findingForm.reset({ condition: '', surfaces: [], diagnosis: '', notes: '' });
    this.findingErrors = [];
    this.findingInvalid = { condition: false, surfaces: false, notes: false, diagnosis: false };
  }

  toggleSurface(code: SurfaceCode, checked: boolean): void {
    const current = this.findingForm.controls.surfaces.value;
    this.findingForm.controls.surfaces.setValue(checked ? [...current.filter(item => item !== code), code] : current.filter(item => item !== code));
  }

  addFinding(): void {
    if (this.selectedPiece === null || !this.editable) return;
    const value = this.findingForm.getRawValue();
    const condition = this.selectedCondition;
    const errors: string[] = [];
    const invalid = { condition: false, surfaces: false, notes: false, diagnosis: false };
    if (!condition) { errors.push(tr('DENTISTRY.ODONTOGRAM.ERR_CONDICION')); invalid.condition = true; }
    const surfaces = condition?.scope === 'whole' ? [] : this.pieceSurfaces.filter(code => value.surfaces.includes(code));
    if (condition?.scope === 'surfaces' && surfaces.length === 0) { errors.push(tr('DENTISTRY.ODONTOGRAM.SUPERFICIES_AYUDA')); invalid.surfaces = true; }
    if (condition?.requires_note && !value.notes.trim()) { errors.push(tr('DENTISTRY.ODONTOGRAM.NOTA_OBLIGATORIA')); invalid.notes = true; }
    if (value.diagnosis.length > DIAGNOSIS_MAX || value.notes.length > NOTES_MAX) {
      errors.push(tr('DENTISTRY.ODONTOGRAM.ERR_LARGO'));
      invalid.diagnosis = value.diagnosis.length > DIAGNOSIS_MAX;
      invalid.notes = invalid.notes || value.notes.length > NOTES_MAX;
    }
    if (condition && this.selectedFindings.some(finding => finding.condition === condition.code)) { errors.push(tr('DENTISTRY.ODONTOGRAM.ERR_DUPLICADO')); invalid.condition = true; }
    this.findingInvalid = invalid;
    this.findingErrors = errors;
    if (errors.length || !condition) {
      const first = invalid.condition ? 'odo-condition'
        : invalid.surfaces ? `odo-surface-${this.pieceSurfaces[0] ?? ''}`
          : invalid.diagnosis ? 'odo-diagnosis' : invalid.notes ? 'odo-notes' : '';
      this.focusFirst(first ? [first] : []);
      return;
    }
    this.findings = [...this.findings, {
      piece: this.selectedPiece, surfaces, condition: condition.code, diagnosis: value.diagnosis.trim(), notes: value.notes.trim(),
    }];
    this.resetFindingForm();
    this.markDirty();
  }

  removeFinding(finding: Finding): void {
    this.findings = this.findings.filter(item => item !== finding);
    this.markDirty();
  }

  addGeneral(): void {
    if (!this.editable) return;
    const value = this.generalForm.getRawValue();
    this.generalErrors = [];
    this.generalInvalid = false;
    if (!value.diagnosis.trim()) this.generalErrors.push(tr('DENTISTRY.ODONTOGRAM.ERR_DIAGNOSTICO'));
    if (value.diagnosis.length > DIAGNOSIS_MAX || value.notes.length > NOTES_MAX) this.generalErrors.push(tr('DENTISTRY.ODONTOGRAM.ERR_LARGO'));
    if (this.generalErrors.length) { this.generalInvalid = true; this.focusFirst(['odo-general-diagnosis']); return; }
    this.generalFindings = [...this.generalFindings, { diagnosis: value.diagnosis.trim(), notes: value.notes.trim() }];
    this.generalForm.reset({ diagnosis: '', notes: '' });
    this.markDirty();
  }

  removeGeneral(finding: GeneralFinding): void {
    this.generalFindings = this.generalFindings.filter(item => item !== finding);
    this.markDirty();
  }

  // ----- Operaciones -----
  private input(): EvaluationInput {
    const header = this.headerForm.getRawValue();
    return {
      dentition: header.dentition, clinical_date: header.clinical_date, professional_id: header.professional_id || null,
      findings: this.findings.map(({ piece, surfaces, condition, diagnosis, notes }) => ({ piece, surfaces, condition, diagnosis, notes })),
      general_findings: this.generalFindings.map(({ diagnosis, notes }) => ({ diagnosis, notes })),
    };
  }

  private persist(): Observable<Evaluation> {
    if (this.isNew) return this.api.create(this.id, this.input());
    if (this.dirty && this.current) return this.api.update(this.current.id, this.input());
    return of(this.current as Evaluation);
  }

  private run(work: () => Observable<Evaluation>, message: string, after?: () => void): void {
    if (this.busy) return;
    this.busy = true;
    this.state = 'saving';
    this.error = '';
    this.success = '';
    this.saveError = '';
    work().pipe(takeUntilDestroyed(this.destroyRef), finalize(() => { this.busy = false; })).subscribe({
      next: evaluation => {
        this.applyEvaluation(evaluation);
        this.state = 'saved';
        this.success = message;
        this.refreshList();
        after?.();
      },
      error: error => { this.state = 'error'; this.saveError = evaluationError(error); },
    });
  }

  saveDraft(): void {
    if (!this.editable || this.headerForm.invalid) { this.headerForm.markAllAsTouched(); this.focusFirst(['odo-date']); return; }
    this.run(() => this.persist(), tr('DENTISTRY.ODONTOGRAM.OK_BORRADOR'));
  }

  openConfirm(dialog: TemplateRef<unknown>): void {
    if (this.busy || !(this.isNew || this.can('confirm')) || this.headerForm.invalid) return;
    this.modal.open(dialog, { centered: true, backdrop: 'static' }).result.then(
      () => this.run(() => this.persist().pipe(
        // Si crear/guardar tuvo éxito y confirmar falla, la pantalla ya refleja el borrador del servidor y el reintento lo confirma.
        tap(evaluation => { if (evaluation !== this.current) { this.applyEvaluation(evaluation); this.refreshList(); } }),
        switchMap(evaluation => this.api.confirm(evaluation.id)),
      ), tr('DENTISTRY.ODONTOGRAM.OK_CONFIRMADA')),
      () => undefined,
    );
  }

  openAmend(dialog: TemplateRef<unknown>): void {
    if (this.busy || !this.can('amend') || !this.current) return;
    this.reasonControl.reset('');
    const source = this.current;
    this.modal.open(dialog, { centered: true, backdrop: 'static' }).result.then(
      (reason: string) => this.run(() => this.api.amend(source.id, reason.trim()), tr('DENTISTRY.ODONTOGRAM.OK_CORRECCION')),
      () => undefined,
    );
  }

  openDiscard(dialog: TemplateRef<unknown>): void {
    if (this.busy || !this.editable) return;
    if (this.isNew) { this.cancelNew(); return; }
    const source = this.current;
    if (!source || !this.can('discard')) return;
    this.modal.open(dialog, { centered: true, backdrop: 'static' }).result.then(() => {
      this.busy = true;
      this.state = 'saving';
      this.api.discard(source.id).pipe(takeUntilDestroyed(this.destroyRef), finalize(() => { this.busy = false; })).subscribe({
        next: () => { this.dirty = false; this.success = tr('DENTISTRY.ODONTOGRAM.OK_DESCARTADO'); this.current = null; this.load(); },
        error: error => { this.state = 'error'; this.saveError = evaluationError(error); },
      });
    }, () => undefined);
  }

  private cancelNew(): void {
    this.dirty = false;
    this.isNew = false;
    this.load();
  }
}
