import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe } from '@angular/common';
import { Component, DestroyRef, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { forkJoin } from 'rxjs';
import {
  WhatsappApiError, WhatsappConnection, WhatsappFieldErrors, WhatsappTemplate, templateBadge, templateStatusLabel,
} from '../../models/whatsapp';
import { WhatsappApiService } from '../../services/whatsapp-api.service';

@Component({
  selector: 'app-whatsapp-integration',
  templateUrl: './whatsapp-integration.component.html',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink, DatePipe],
})
export class WhatsappIntegrationComponent implements OnInit {
  private api = inject(WhatsappApiService);
  private fb = inject(FormBuilder).nonNullable;
  private destroyRef = inject(DestroyRef);

  readonly templateBadge = templateBadge;
  readonly templateStatusLabel = templateStatusLabel;

  connection: WhatsappConnection | null = null;
  templates: WhatsappTemplate[] = [];
  loading = false;
  loadError = '';
  saving = false;
  saveError = '';
  saved = false;
  fieldErrors: WhatsappFieldErrors = {};
  confirmingChange = false;
  syncing = false;
  syncError = '';
  testing = false;
  testResult: { ok: boolean; message: string } | null = null;
  copied = '';

  readonly form = this.fb.group({
    wabaId: ['', [Validators.required, Validators.pattern(/^\d+$/)]],
    phoneNumberId: ['', [Validators.required, Validators.pattern(/^\d+$/)]],
    displayPhone: [''],
    secretRef: ['', [Validators.required, Validators.pattern(/^WHATSAPP_[A-Z0-9_]+$/)]],
    appSecretRef: ['', [Validators.required, Validators.pattern(/^WHATSAPP_[A-Z0-9_]+$/)]],
  });

  readonly testForm = this.fb.group({
    to: ['', [Validators.required]],
    templateId: ['', [Validators.required]],
  });

  ngOnInit(): void {
    this.load();
  }

  get approvedTemplates(): WhatsappTemplate[] {
    return this.templates.filter((t) => t.status === 'APPROVED');
  }

  get canSendTest(): boolean {
    return !!this.connection && this.connection.status === 'active';
  }

  load(): void {
    this.loading = true;
    this.loadError = '';
    forkJoin({ connection: this.api.getConnection(), templates: this.api.listTemplates() })
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: ({ connection, templates }) => {
          this.loading = false;
          this.templates = templates;
          this.apply(connection);
        },
        error: (err: WhatsappApiError) => {
          this.loading = false;
          this.loadError = err.message;
        },
      });
  }

  private apply(connection: WhatsappConnection): void {
    this.connection = connection;
    this.form.reset({
      wabaId: connection.wabaId, phoneNumberId: connection.phoneNumberId, displayPhone: connection.displayPhone,
      secretRef: connection.secretRef, appSecretRef: connection.appSecretRef,
    });
  }

  /** Cambiar WABA o número cambia el remitente: se pide confirmación antes de guardar. */
  private changesSender(): boolean {
    const c = this.connection;
    const v = this.form.getRawValue();
    return !!c && c.configured && (c.wabaId !== v.wabaId.trim() || c.phoneNumberId !== v.phoneNumberId.trim());
  }

  submit(confirmed = false): void {
    if (this.form.invalid || this.saving) return;
    if (!confirmed && this.changesSender()) {
      this.confirmingChange = true;
      return;
    }
    this.confirmingChange = false;
    this.saving = true;
    this.saveError = '';
    this.saved = false;
    this.fieldErrors = {};
    this.api.saveConnection(this.form.getRawValue()).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (connection) => {
        this.saving = false;
        this.saved = true;
        this.apply(connection);
      },
      error: (err: WhatsappApiError) => {
        this.saving = false;
        this.saveError = err.message;
        this.fieldErrors = err.fieldErrors;
      },
    });
  }

  cancelChange(): void {
    this.confirmingChange = false;
  }

  sync(): void {
    if (this.syncing) return;
    this.syncing = true;
    this.syncError = '';
    this.api.syncTemplates().pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (templates) => {
        this.syncing = false;
        this.templates = templates;
        this.api.getConnection().pipe(takeUntilDestroyed(this.destroyRef)).subscribe((c) => (this.connection = c));
      },
      error: (err: WhatsappApiError) => {
        this.syncing = false;
        this.syncError = err.message;
      },
    });
  }

  sendTest(): void {
    if (this.testForm.invalid || this.testing) return;
    this.testing = true;
    this.testResult = null;
    const { to, templateId } = this.testForm.getRawValue();
    this.api.sendTestMessage(to, templateId).pipe(takeUntilDestroyed(this.destroyRef)).subscribe({
      next: (result) => {
        this.testing = false;
        this.testResult = { ok: true, message: result.status };
      },
      error: (err: WhatsappApiError) => {
        this.testing = false;
        this.testResult = { ok: false, message: err.message };
      },
    });
  }

  copy(value: string, key: string): void {
    void navigator.clipboard?.writeText(value).then(() => (this.copied = key));
  }

  statusClass(): string {
    switch (this.connection?.status) {
      case 'active':
        return 'col-green';
      case 'error':
        return 'col-red';
      case 'pending':
        return 'col-orange';
      default:
        return 'col-blue';
    }
  }
}
