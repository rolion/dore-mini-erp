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

  select(tab: SettingsTab): void {
    this.tab = tab;
  }
}
