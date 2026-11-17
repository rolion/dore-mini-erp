import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { PostingConfigPanelComponent } from '../../../accounting/components/posting-config-panel/posting-config-panel.component';

/** Configuración de Gastos: cuentas de los asientos automáticos (cuenta de gasto por categoría y cuenta de pago). */
@Component({
  selector: 'app-expense-settings',
  templateUrl: './expense-settings.component.html',
  imports: [TranslatePipe, RouterLink, PostingConfigPanelComponent],
})
export class ExpenseSettingsComponent {}
