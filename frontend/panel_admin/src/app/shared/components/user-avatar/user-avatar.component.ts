import { ChangeDetectionStrategy, Component, input } from '@angular/core';

/** Avatar circular con las iniciales de la persona (estilo `.avatar[data-initial]` de la plantilla). */
@Component({
  selector: 'app-user-avatar',
  template: `<figure
    class="avatar"
    [class.avatar-sm]="size() === 'sm'"
    [class.avatar-xl]="size() === 'xl'"
    [attr.data-initial]="initials()"
    role="img"
    [attr.aria-label]="label()"
  ></figure>`,
  styles: [':host { display: inline-block; line-height: 0; } figure { display: block; }'],
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class UserAvatarComponent {
  readonly initials = input.required<string>();
  /** Nombre completo, para lectores de pantalla. */
  readonly label = input<string>('');
  readonly size = input<'sm' | 'xl'>('xl');
}
