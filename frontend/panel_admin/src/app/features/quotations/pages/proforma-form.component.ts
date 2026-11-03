import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormArray, FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { debounceTime, finalize } from 'rxjs';
import { Customer } from '../../customers/models/customer';
import { CustomersApiService } from '../../customers/services/customers-api.service';
import { CatalogService } from '../../services/models/service';
import { ServicesApiService } from '../../services/services/services-api.service';
import { NOTES_MAX_LENGTH, Proforma, ProformaFailure, ProformaInput, previewSubtotal } from '../models/proforma';
import { ProformasApiService } from '../services/proformas-api.service';

/** Alta y edición de borrador (plantilla Formulario + tabla de líneas editable). El servidor recalcula todo. */
@Component({
  selector: 'app-proforma-form',
  imports: [ReactiveFormsModule, RouterLink],
  templateUrl: './proforma-form.component.html',
})
export class ProformaFormComponent implements OnInit {
  private api = inject(ProformasApiService);
  private customersApi = inject(CustomersApiService);
  private servicesApi = inject(ServicesApiService);
  private router = inject(Router);
  private route = inject(ActivatedRoute);
  private destroyRef = inject(DestroyRef);
  private fb = inject(FormBuilder).nonNullable;

  readonly notesMax = NOTES_MAX_LENGTH;
  readonly customerSearch = this.fb.control('');
  readonly form = this.fb.group({
    customer_id: ['', Validators.required],
    date: [this.today(), Validators.required],
    valid_until: '',
    notes: ['', Validators.maxLength(NOTES_MAX_LENGTH)],
    lines: this.fb.array([this.newLine()]),
  });

  proformaId: string | null = null;
  header = '';
  customers: Customer[] = [];
  services: CatalogService[] = [];
  canEditPrice = true;
  saving = false;
  loading = true;
  error = '';
  fields: Record<string, string> = {};
  lineErrors: Record<string, string>[] = [];

  get lines(): FormArray {
    return this.form.controls.lines;
  }

  ngOnInit(): void {
    this.proformaId = this.route.snapshot.paramMap.get('id');
    let pending = this.proformaId ? 3 : 2;
    const done = () => { if (--pending === 0) this.loading = false; };
    const fail = () => { this.error = 'No se pudieron cargar los datos del formulario.'; done(); };
    this.servicesApi.list({ active: true, pageSize: 100 }).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: page => { this.services = page.results; done(); }, error: fail });
    this.searchCustomers('', done);
    this.customerSearch.valueChanges.pipe(debounceTime(300), takeUntilDestroyed(this.destroyRef))
      .subscribe(term => this.searchCustomers(term));
    if (this.proformaId) {
      this.api.get(this.proformaId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
        next: proforma => { this.load(proforma); done(); },
        error: (failure: ProformaFailure) => { this.error = failure.message; done(); },
      });
    }
  }

  private today(): string {
    return new Intl.DateTimeFormat('en-CA', {
      timeZone: 'America/La_Paz', year: 'numeric', month: '2-digit', day: '2-digit',
    }).format(new Date());
  }

  private newLine(values: { id?: string; service_id?: string; description?: string; quantity?: string; unit_price?: string } = {}) {
    return this.fb.group({
      id: values.id ?? '',
      service_id: [values.service_id ?? '', Validators.required],
      description: values.description ?? '',
      quantity: [values.quantity ?? '1', [Validators.required, Validators.min(0.01), Validators.max(9999.99)]],
      unit_price: [values.unit_price ?? '', [Validators.required, Validators.min(0)]],
    });
  }

  private load(proforma: Proforma): void {
    this.header = `${proforma.number} · v${proforma.version}`;
    this.canEditPrice = proforma.can_edit_price;
    if (!proforma.allowed_actions.includes('edit')) {
      this.error = 'Solo se puede editar una proforma en borrador.';
    }
    this.form.patchValue({
      customer_id: proforma.customer_id, date: proforma.date, valid_until: proforma.valid_until ?? '', notes: proforma.notes,
    });
    if (!this.customers.some(customer => customer.id === proforma.customer_id)) {
      this.customers = [...this.customers, { id: proforma.customer_id, name: proforma.customer_name } as Customer];
    }
    this.lines.clear();
    for (const line of proforma.lines) this.lines.push(this.newLine(line));
    this.form.markAsPristine();
  }

  private searchCustomers(term: string, done?: () => void): void {
    this.customersApi.list({ active: true, search: term.trim(), pageSize: 50 }).pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: page => {
          const selected = this.customers.filter(customer => customer.id === this.form.controls.customer_id.value);
          this.customers = [...selected, ...page.results.filter(c => !selected.some(s => s.id === c.id))];
          done?.();
        },
        error: () => { this.error = 'No se pudieron cargar los clientes.'; done?.(); },
      });
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
    if (this.form.invalid || this.saving || this.error === 'Solo se puede editar una proforma en borrador.') return;
    const value = this.form.getRawValue();
    const input: ProformaInput = {
      customer_id: value.customer_id,
      date: value.date,
      valid_until: value.valid_until || null,
      notes: value.notes,
      // Solo se envía el precio si la persona lo editó: si no, el servidor usa el vigente (nuevas) o el congelado.
      lines: (value.lines as { id: string; service_id: string; quantity: string; unit_price: string }[]).map((line, index) => ({
        ...(line.id ? { id: line.id } : {}),
        service_id: line.service_id,
        quantity: String(line.quantity),
        ...(this.lines.at(index).get('unit_price')?.dirty ? { unit_price: String(line.unit_price) } : {}),
      })),
    };
    this.saving = true;
    this.error = '';
    this.fields = {};
    this.lineErrors = [];
    const request = this.proformaId ? this.api.update(this.proformaId, input) : this.api.create(input);
    request.pipe(takeUntilDestroyed(this.destroyRef), finalize(() => this.saving = false)).subscribe({
      next: proforma => {
        this.form.markAsPristine();
        void this.router.navigate(['/pocketbiz/quotations/proformas', proforma.id]);
      },
      error: (failure: ProformaFailure) => {
        this.error = failure.message;
        this.fields = failure.fields;
        this.lineErrors = failure.lines;
      },
    });
  }
}
