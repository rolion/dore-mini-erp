import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccountsTabComponent } from '../../components/accounts-tab/accounts-tab.component';

/** Contabilidad › Cuentas: el plan de cuentas de la empresa (la lista y los diálogos son los de siempre). */
@Component({
  selector: 'app-accounts-page',
  templateUrl: './accounts-page.component.html',
  imports: [TranslatePipe, RouterLink, AccountsTabComponent],
})
export class AccountsPageComponent {}
