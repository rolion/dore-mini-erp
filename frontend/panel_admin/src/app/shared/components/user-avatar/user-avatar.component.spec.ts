import { ComponentFixture, TestBed } from '@angular/core/testing';
import { UserAvatarComponent } from './user-avatar.component';

describe('UserAvatarComponent', () => {
  let fixture: ComponentFixture<UserAvatarComponent>;

  const render = (inputs: Record<string, unknown>): HTMLElement => {
    fixture = TestBed.createComponent(UserAvatarComponent);
    for (const [name, value] of Object.entries(inputs)) {
      fixture.componentRef.setInput(name, value);
    }
    fixture.detectChanges();
    return (fixture.nativeElement as HTMLElement).querySelector('figure') as HTMLElement;
  };

  it('shows the initials and exposes the full name to assistive tech (AC-07)', () => {
    const figure = render({ initials: 'MQ', label: 'María Quispe', size: 'xl' });
    expect(figure.getAttribute('data-initial')).toBe('MQ');
    expect(figure.getAttribute('role')).toBe('img');
    expect(figure.getAttribute('aria-label')).toBe('María Quispe');
    expect(figure.classList).toContain('avatar-xl');
  });

  it('supports the small size', () => {
    const figure = render({ initials: 'A', size: 'sm' });
    expect(figure.classList).toContain('avatar-sm');
    expect(figure.classList).not.toContain('avatar-xl');
  });
});
