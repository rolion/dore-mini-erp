import { Component } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';

/** Contabilidad › Saldos: pantalla «Próximamente» hasta que existan los saldos sobre el libro de asientos (CONT-04/05). */
@Component({
  selector: 'app-balances-page',
  templateUrl: './balances-page.component.html',
  imports: [TranslatePipe, RouterLink],
})
export class BalancesPageComponent {}
