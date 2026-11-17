import { Component, input, output } from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { PostingIssue } from '../../models/receivable';

/**
 * Aviso accionable de configuración contable incompleta (409 `posting_configuration_missing`): lista lo que falta y
 * enlaza a la pestaña «Asientos automáticos» de la configuración del módulo. Presentacional: no decide nada.
 */
@Component({
  selector: 'app-posting-issues-alert',
  imports: [RouterLink, TranslatePipe],
  template: `
    @if (issues().length) {
      <div class="alert alert-warning bg-warning-subtle text-warning-emphasis border-warning-subtle mt-2 mb-0"
           role="alert" data-testid="alert-posting-issues">
        <strong>{{ 'RECEIVABLES.CONFIG_INCOMPLETA' | translate }}</strong>
        <ul class="mb-1">
          @for (issue of issues(); track $index) { <li>{{ issue.message }}</li> }
        </ul>
        <a [routerLink]="settingsLink()" [queryParams]="{ tab: 'posting' }" class="text-reset text-decoration-underline"
           data-testid="link-posting-settings" (click)="navigate.emit()">{{ 'RECEIVABLES.IR_A_CONFIG' | translate }}</a>
      </div>
    }
  `,
})
export class PostingIssuesAlertComponent {
  readonly issues = input.required<PostingIssue[]>();
  readonly settingsLink = input<string>('/pocketbiz/receivables/settings');
  /** Se emite al seguir el enlace (para que un diálogo se cierre). */
  readonly navigate = output<void>();
}
