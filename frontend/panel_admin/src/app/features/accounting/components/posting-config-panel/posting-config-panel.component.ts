import { Component, DestroyRef, Input, OnInit, inject } from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { Observable, finalize, forkJoin } from 'rxjs';
import { tr } from '../../../../core/i18n/translate';
import { Account, AccountClassCode, AccountingApiError, FLOW_CURRENCY } from '../../models/accounting';
import { PostingConfig, PostingIssue, PostingModule, PreviewLine, accountLabel } from '../../models/posting-config';
import { AccountingApiService } from '../../services/accounting-api.service';
import { PostingConfigApiService } from '../../services/posting-config-api.service';

export type RowKind = 'role' | 'method' | 'category';

/** Una fila editable: una cuenta elegida para un rol, un método de pago o una categoría de gasto. */
export interface ConfigRow {
  key: string;
  kind: RowKind;
  /** Código del rol o del método, o id de la categoría. */
  id: string;
  /** Texto propio (método o categoría); los roles se traducen por su código. */
  label: string;
  accountClass: AccountClassCode;
  /** Exige tipo Caja/Banco/Billetera (cuenta de dinero). */
  money: boolean;
  isActive: boolean;
  /** Otros módulos que usan el mismo rol (se comparte la cuenta). */
  sharedWith: string[];
  control: FormControl<string>;
  original: string;
  issue: string | null;
  saving: boolean;
  saved: boolean;
  error: string;
}

/**
 * Panel «Asientos automáticos» de un módulo (CONT-12): elige las cuentas de cada evento y muestra el asiento
 * Debe/Haber resultante, recalculado al elegir. El servidor valida empresa, cuenta activa y clasificación.
 */
@Component({
  selector: 'app-posting-config-panel',
  templateUrl: './posting-config-panel.component.html',
  styleUrl: './posting-config-panel.component.scss',
  imports: [TranslatePipe, ReactiveFormsModule, RouterLink],
})
export class PostingConfigPanelComponent implements OnInit {
  @Input({ required: true }) module!: PostingModule;

  config: PostingConfig | null = null;
  accounts: Account[] = [];
  roleRows: ConfigRow[] = [];
  methodRows: ConfigRow[] = [];
  categoryRows: ConfigRow[] = [];
  loading = false;
  loadError = '';

  private api = inject(PostingConfigApiService);
  private accountingApi = inject(AccountingApiService);
  private destroyRef = inject(DestroyRef);

  ngOnInit(): void {
    this.reload();
  }

  reload(): void {
    this.loading = true;
    this.loadError = '';
    forkJoin({ config: this.api.get(this.module), accounts: this.accountingApi.listAccounts(true) })
      .pipe(
        finalize(() => (this.loading = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: ({ config, accounts }) => {
          this.accounts = accounts;
          this.apply(config);
        },
        error: (err: AccountingApiError) => (this.loadError = err.message),
      });
  }

  /** Cuentas elegibles para la fila: activas, en BOB, de la clasificación del rol (y con tipo de dinero si aplica). */
  options(row: ConfigRow): Account[] {
    return this.accounts.filter(
      (a) => a.isActive && a.currency === FLOW_CURRENCY && a.accountClass === row.accountClass && (!row.money || !!a.kind),
    );
  }

  label(account: Account): string {
    return accountLabel(account);
  }

  isDirty(row: ConfigRow): boolean {
    return row.control.value !== row.original;
  }

  /** Faltantes actuales del módulo (con Contabilidad habilitada): una línea por mensaje distinto. */
  get issues(): PostingIssue[] {
    const seen = new Set<string>();
    return (this.config?.events ?? [])
      .flatMap((event) => event.issues)
      .filter((issue) => !seen.has(issue.message) && !!seen.add(issue.message));
  }

  /** Cuenta de una línea del asiento previsto según lo elegido ahora (aún sin guardar). */
  previewAccount(line: PreviewLine): { text: string; state: 'ok' | 'missing' | 'invalid' } {
    const row = this.roleRows.find((r) => r.id === line.role);
    if (!row) {
      return { text: '', state: 'missing' };
    }
    const chosen = this.accounts.find((a) => a.id === row.control.value);
    if (chosen) {
      return { text: this.label(chosen), state: 'ok' };
    }
    if (row.control.value && line.account) {
      // La cuenta guardada ya no es elegible (deshabilitada o reclasificada).
      return { text: accountLabel(line.account), state: 'invalid' };
    }
    return { text: '', state: 'missing' };
  }

  save(row: ConfigRow): void {
    if (row.saving) {
      return;
    }
    const accountId = row.control.value || null;
    row.saving = true;
    row.saved = false;
    row.error = '';
    this.send(row, accountId)
      .pipe(
        finalize(() => (row.saving = false)),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: () => {
          row.saved = true;
          this.refresh();
        },
        error: (err: AccountingApiError) => (row.error = err.fieldErrors['accountId']?.join(' ') || err.message),
      });
  }

  private send(row: ConfigRow, accountId: string | null): Observable<unknown> {
    if (row.kind === 'method') {
      return this.accountingApi.configureMethod(row.id, accountId, row.isActive);
    }
    return row.kind === 'role' ? this.api.setRoleAccount(row.id, accountId) : this.api.setCategoryAccount(row.id, accountId);
  }

  /** Relee la configuración tras guardar (estado, faltantes y vista previa) sin perder lo que se está editando. */
  private refresh(): void {
    this.api
      .get(this.module)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe({ next: (config) => this.apply(config, true), error: () => undefined });
  }

  private apply(config: PostingConfig, keepEdits = false): void {
    const edits = new Map<string, ConfigRow>([...this.roleRows, ...this.methodRows, ...this.categoryRows].map((r) => [r.key, r]));
    const build = (row: Omit<ConfigRow, 'key' | 'control' | 'original' | 'saving' | 'saved' | 'error'>, accountId: string | undefined): ConfigRow => {
      const key = `${row.kind}:${row.id}`;
      const previous = keepEdits ? edits.get(key) : undefined;
      const original = accountId ?? '';
      // Una fila que se está editando o acaba de guardarse conserva su estado; el resto toma el valor del servidor.
      if (previous && (this.isDirty(previous) || previous.saved || previous.error)) {
        // Se actualiza la misma fila (no una copia): un guardado en curso termina sobre ella.
        return Object.assign(previous, row, { original });
      }
      return { ...row, key, original, control: new FormControl(original, { nonNullable: true }), saving: false, saved: false, error: '' };
    };
    this.config = config;
    this.roleRows = config.roles.map((r) =>
      build(
        { kind: 'role', id: r.role, label: r.label, accountClass: r.accountClass, money: false, isActive: true, sharedWith: r.sharedWith.map((s) => s.label), issue: r.issue },
        r.account?.id,
      ),
    );
    this.methodRows = config.methods.map((m) =>
      build({ kind: 'method', id: m.code, label: m.label, accountClass: 'ASSET', money: true, isActive: m.isActive, sharedWith: [], issue: m.issue }, m.account?.id),
    );
    this.categoryRows = config.categories.map((c) =>
      build(
        { kind: 'category', id: c.classificationId, label: c.name, accountClass: 'EXPENSE', money: false, isActive: c.isActive, sharedWith: [], issue: c.issue },
        c.account?.id,
      ),
    );
  }

  /** Texto de la pista bajo el selector: qué clasificación se necesita. */
  hint(row: ConfigRow): string {
    return row.money
      ? tr('ACCOUNTING.POSTING.HINT_MONEY')
      : tr('ACCOUNTING.POSTING.HINT_CLASS', { p0: tr(`ACCOUNTING.POSTING.CLASSES.${row.accountClass}`) });
  }
}
