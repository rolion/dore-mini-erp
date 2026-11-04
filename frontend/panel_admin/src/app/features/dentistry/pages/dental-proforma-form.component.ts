import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { finalize } from 'rxjs';
import { HasUnsavedChanges } from '../../../core/guard/unsaved-changes.guard';
import { tr } from '../../../core/i18n/translate';
import { fetchAll } from '../../agenda/services/fetch-all';
import { CatalogService } from '../../services/models/service';
import { ServicesApiService } from '../../services/services/services-api.service';
import {
  DENTAL_PIECE_MAX_LENGTH, DentalProforma, DentalProformaFailure, DentalProformaInput, PROFORMA_NOTES_MAX_LENGTH,
  previewSubtotal,
} from '../models/dental-proforma';
import { DentistryApiService } from '../services/dentistry-api.service';
import { DentalProformasApiService } from '../services/dental-proformas-api.service';

/** Alta y edición de borrador de una proforma odontológica: tabla de líneas con pieza dental. El servidor recalcula todo. */
@Component({
  selector: 'app-dental-proforma-form',
  imports: [ReactiveFormsModule, RouterLink, TranslatePipe],
  templateUrl: './dental-proforma-form.component.html',
})
export class DentalProformaFormComponent implements OnInit, HasUnsavedChanges {
  private api = inject(DentalProformasApiService);
  private patientsApi = inject(DentistryApiService);
  private servicesApi = inject(ServicesApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly notesMax = PROFORMA_NOTES_MAX_LENGTH;
  readonly pieceMax = DENTAL_PIECE_MAX_LENGTH;
  readonly form = this.fb.group({
    date: [this.today(), Validators.required],
    valid_until: '',
    notes: ['', Validators.maxLength(PROFORMA_NOTES_MAX_LENGTH)],
    lines: this.fb.array([this.newLine()]),
  });

  proformaId: string | null = null;
  patientId = '';
  patientName = '';
  header = '';
  services: CatalogService[] = [];
  canEditPrice = true;
  saving = false;
  readOnly = false;
  loading = true;
  error = '';
  fields: Record<string, string> = {};
  lineErrors: Record<string, string>[] = [];

  get lines(): FormArray {
    return this.form.controls.lines;
  }

  ngOnInit(): void {
    const params = this.route.snapshot.paramMap;
    this.proformaId = params.get('proformaId');
    this.patientId = params.get('patientId') ?? '';
    let pending = 2;
    const done = () => { if (--pending === 0) this.loading = false; };
    const fail = () => { this.error = tr('DENTISTRY.PROFORMAS.ERR_CARGA_FORM'); done(); };
    fetchAll(page => this.servicesApi.list({ active: true, pageSize: 100, page })).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: services => { this.services = services; done(); }, error: fail });
    if (this.proformaId) {
      this.api.get(this.proformaId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: proforma => { this.load(proforma); done(); },
        error: (failure: DentalProformaFailure) => { this.error = failure.message; done(); },
      });
    } else {
      this.patientsApi.get(this.patientId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: patient => {
          this.patientName = patient.customer.name;
          if (!patient.active) { this.error = tr('DENTISTRY.PROFORMAS.ARCHIVADO'); this.readOnly = true; }
          done();
        },
        error: () => { this.error = tr('DENTISTRY.PROFORMAS.ERR_PACIENTE'); this.readOnly = true; done(); },
      });
    }
  }

  private today(): string {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(new Date());
  }

  private newLine(values: { id?: string; service_id?: string; description?: string; quantity?: string; unit_price?: string; dental_piece?: string } = {}) {
    return this.fb.group({
      id: values.id ?? '',
      service_id: [values.service_id ?? '', Validators.required],
      description: values.description ?? '',
      quantity: [values.quantity ?? '1', [Validators.required, Validators.min(0.01), Validators.max(9999.99)]],
      unit_price: [values.unit_price ?? '', [Validators.required, Validators.min(0)]],
      dental_piece: [values.dental_piece ?? '', [Validators.maxLength(DENTAL_PIECE_MAX_LENGTH)]],
    });
  }

  private load(proforma: DentalProforma): void {
    this.patientId = proforma.customer_id;
    this.patientName = proforma.patient_name;
    this.header = `${proforma.number} · v${proforma.version}`;
    this.canEditPrice = proforma.can_edit_price;
    if (!proforma.allowed_actions.includes('edit')) {
      this.error = tr('DENTISTRY.PROFORMAS.ERR_SOLO_BORRADOR');
      this.readOnly = true;
    }
    this.form.patchValue({ date: proforma.date, valid_until: proforma.valid_until ?? '', notes: proforma.notes });
    this.lines.clear();
    for (const line of proforma.lines) this.lines.push(this.newLine(line));
    this.form.markAsPristine();
  }

  hasUnsavedChanges(): boolean {
    return this.form.dirty && !this.saving;
  }

  isFrozen(index: number): boolean {
    return !!this.lines.at(index).get('id')?.value;
  }

  addLine(): void {
    this.lines.push(this.newLine());
    this.form.markAsDirty();
  }

  removeLine(index: number): void {
    this.lines.removeAt(index);
    this.lineErrors = [];
    this.form.markAsDirty();
  }

  /** Al elegir un servicio nuevo se muestra su precio vigente; el servidor lo captura al guardar. */
  pickService(index: number): void {
    const line = this.lines.at(index);
    const service = this.services.find(item => item.id === line.get('service_id')?.value);
    if (service) line.patchValue({ description: service.name, unit_price: service.basePrice });
  }

  subtotal(index: number): string {
    const { quantity, unit_price } = this.lines.at(index).getRawValue() as { quantity: string; unit_price: string };
    return previewSubtotal(quantity, unit_price).toFixed(2);
  }

  get total(): string {
    return this.lines.controls.reduce((sum, _, index) => sum + Number(this.subtotal(index)), 0).toFixed(2);
  }

  submit(): void {
    this.form.markAllAsTouched();
    if (this.form.invalid || this.saving || this.readOnly) return;
    const value = this.form.getRawValue();
    const input: DentalProformaInput = {
      date: value.date,
      valid_until: value.valid_until || null,
      notes: value.notes,
      // Solo se envía el precio si la persona lo editó: si no, el servidor usa el vigente (nuevas) o el congelado.
      lines: (value.lines as { id: string; service_id: string; quantity: string; unit_price: string; dental_piece: string }[])
        .map((line, index) => ({
          ...(line.id ? { id: line.id } : {}),
          service_id: line.service_id,
          quantity: String(line.quantity),
          ...(this.lines.at(index).get('unit_price')?.dirty ? { unit_price: String(line.unit_price) } : {}),
          dental_piece: String(line.dental_piece ?? ''),
        })),
    };
    this.saving = true;
    this.error = '';
    this.fields = {};
    this.lineErrors = [];
    const request = this.proformaId ? this.api.update(this.proformaId, input) : this.api.create(this.patientId, input);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false)).subscribe({
      next: proforma => {
        this.form.markAsPristine();
        void this.router.navigate(['/pocketbiz/dentistry/proformas', proforma.id]);
      },
      error: (failure: DentalProformaFailure) => {
        this.error = failure.message;
        this.fields = failure.fields;
        this.lineErrors = failure.lines;
      },
    });
  }
}
