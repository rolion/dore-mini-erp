import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccountsTabComponent } from '../../components/accounts-tab/accounts-tab.component';
import { MethodsTabComponent } from '../../components/methods-tab/methods-tab.component';

export type SettingsTab = 'accounts' | 'methods';

/** Contabilidad › Configuración › Cuentas y Métodos de pago: dos pestañas (cuentas destino y mapeo de métodos). */
@Component({
  selector: 'app-accounting-settings',
  templateUrl: './accounting-settings.component.html',
  imports: [TranslatePipe, RouterLink, AccountsTabComponent, MethodsTabComponent],
})
export class AccountingSettingsComponent {
  tab: SettingsTab = 'accounts';

  readonly tabs: readonly SettingsTab[] = ['accounts', 'methods'];

  select(tab: SettingsTab): void {
    this.tab = tab;
  }

  /** Patrón WAI-ARIA de pestañas: flechas, Inicio y Fin mueven la selección y el foco. */
  onTabKeydown(event: KeyboardEvent): void {
    const last = this.tabs.length - 1;
    const current = this.tabs.indexOf(this.tab);
    const target: Record<string, number> = {
      ArrowRight: current === last ? 0 : current + 1,
      ArrowLeft: current === 0 ? last : current - 1,
      Home: 0,
      End: last,
    };
    const index = target[event.key];
    if (index === undefined) {
      return;
    }
    event.preventDefault();
    this.select(this.tabs[index]);
    const list = (event.currentTarget as HTMLElement).closest('[role="tablist"]');
    list?.querySelector<HTMLElement>(`#tab-${this.tabs[index]}`)?.focus();
  }
}
