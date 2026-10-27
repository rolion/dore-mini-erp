import { Component, DestroyRef, HostListener, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ToastrService } from 'ngx-toastr';
import { HasUnsavedChanges } from '../../../../core/guard/unsaved-changes.guard';
import { SettingsHistoryComponent } from '../../components/settings-history/settings-history.component';
import { Setting, SettingsApiError } from '../../models/setting';
import { SettingsApiService } from '../../services/settings-api.service';

export const MODULE_TITLES: Record<string, string> = {
  sales: 'Ventas',
  purchases: 'Compras',
  inventory: 'Inventario',
};

export const SAVED_MESSAGE = 'Configuración guardada';
export const NO_SETTINGS_MESSAGE =
  'Este módulo aún no tiene ajustes configurables. Cuando haya reglas disponibles aparecerán aquí.';

type Tab = 'general' | 'history';

/** Configuración de un módulo (`data.settingsModule`): pestañas «General» e «Historial de cambios». */
@Component({
  selector: 'app-module-settings',
  templateUrl: './module-settings.component.html',
  imports: [ReactiveFormsModule, RouterLink, SettingsHistoryComponent],
})
export class ModuleSettingsComponent implements OnInit, HasUnsavedChanges {
  readonly module: string = inject(ActivatedRoute).snapshot.data['settingsModule'] ?? '';
  readonly title = MODULE_TITLES[this.module] ?? this.module;
  readonly noSettingsMessage = NO_SETTINGS_MESSAGE;

  tab: Tab = 'general';
  settings: Setting[] = [];
  form = new FormGroup<Record<string, FormControl<string>>>({});
  loading = false;
  saving = false;
  loadError = '';
  /** Error general del servidor (no asociado a un campo). */
  formError = '';
  /** Errores del servidor por clave de ajuste; se limpian al editar ese campo. */
  serverErrors: Record<string, string> = {};

  private saved: Record<string, string> = {};
  private api = inject(SettingsApiService);
  private toastr = inject(ToastrService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.load();
  }

  load(): void {
    this.loading = true;
    this.loadError = '';
    this.api
      .get(this.module)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.loading = false;
          this.apply(result.settings);
        },
        error: (err: SettingsApiError) => {
          this.loading = false;
          this.loadError = err.message;
        },
      });
  }

  select(tab: Tab): void {
    this.tab = tab;
  }

  /** Hay cambios respecto al último valor guardado. */
  get dirty(): boolean {
    return this.settings.some((s) => this.changed(s));
  }

  /** Compara con el último valor guardado; los porcentajes por su valor numérico («100» = «100.00»). */
  private changed(setting: Setting): boolean {
    const current = this.control(setting).value;
    const saved = this.saved[setting.key];
    if (setting.kind === 'percent' && current.trim() !== '' && !Number.isNaN(Number(current))) {
      return Number(current) !== Number(saved);
    }
    return current !== saved;
  }

  hasUnsavedChanges(): boolean {
    return this.dirty;
  }

  @HostListener('window:beforeunload', ['$event'])
  warnBeforeUnload(event: BeforeUnloadEvent): void {
    if (this.dirty) {
      event.preventDefault();
    }
  }

  control(setting: Setting): FormControl<string> {
    return this.form.controls[setting.key];
  }

  errorOf(setting: Setting): string {
    return this.serverErrors[setting.key] ?? '';
  }

  isDefault(setting: Setting): boolean {
    return this.control(setting).value === setting.default;
  }

  defaultLabel(setting: Setting): string {
    if (setting.kind === 'percent') {
      return `${setting.default} %`;
    }
    return setting.choices.find((c) => c.value === setting.default)?.label ?? 'Sin predeterminado';
  }

  restoreDefault(setting: Setting): void {
    this.control(setting).setValue(setting.default);
    this.control(setting).markAsDirty();
  }

  cancel(): void {
    this.form.reset(this.saved);
    this.serverErrors = {};
    this.formError = '';
  }

  save(): void {
    if (!this.dirty || this.saving) {
      return;
    }
    this.saving = true;
    this.serverErrors = {};
    this.formError = '';
    const changed: Record<string, string> = {};
    for (const setting of this.settings) {
      const value = this.control(setting).value;
      if (this.changed(setting)) {
        changed[setting.key] = value;
      }
    }
    this.api
      .save(this.module, changed)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({
        next: (result) => {
          this.saving = false;
          this.apply(result.settings);
          this.toastr.success(SAVED_MESSAGE);
        },
        error: (err: SettingsApiError) => {
          // Los datos introducidos se conservan: solo se muestran los errores.
          this.saving = false;
          this.serverErrors = err.fieldErrors;
          this.formError = Object.keys(err.fieldErrors).length ? '' : err.message;
        },
      });
  }

  private apply(settings: Setting[]): void {
    this.settings = settings;
    this.saved = Object.fromEntries(settings.map((s) => [s.key, s.value]));
    this.form = new FormGroup(
      Object.fromEntries(settings.map((s) => [s.key, new FormControl(s.value, { nonNullable: true })])),
    );
    this.form.valueChanges.pipe(takeUntilDestroyed(this.destroyRef)).subscribe(() => (this.serverErrors = {}));
  }
}
