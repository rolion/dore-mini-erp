import { Component, input, signal } from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';

/**
 * Botón ojo / ojo tachado para mostrar u ocultar una contraseña. Se coloca dentro de un contenedor
 * `position-relative` junto al input, que se recibe en `target`; arranca con la contraseña oculta.
 */
@Component({
  selector: 'app-password-toggle',
  imports: [TranslatePipe, FeatherModule],
  template: `<button type="button" class="password-toggle" (click)="toggle()"
    [attr.aria-label]="(visible() ? 'AUTH.PASSWORD_TOGGLE.OCULTAR' : 'AUTH.PASSWORD_TOGGLE.MOSTRAR') | translate"
    [attr.aria-pressed]="visible()">
    <i-feather [name]="visible() ? 'eye' : 'eye-off'" aria-hidden="true"></i-feather>
  </button>`,
})
export class PasswordToggleComponent {
  readonly target = input.required<HTMLInputElement>();
  readonly visible = signal(false);

  toggle(): void {
    this.visible.update((v) => !v);
    this.target().type = this.visible() ? 'text' : 'password';
  }
}
