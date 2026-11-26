import { Component } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { importProvidersFrom } from '@angular/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTestTranslations } from '../../../core/i18n/testing';
import { PasswordToggleComponent } from './password-toggle.component';

@Component({
  imports: [PasswordToggleComponent],
  template: `<div class="position-relative"><input #pw type="password" value="secreto">
    <app-password-toggle [target]="pw"></app-password-toggle></div>`,
})
class HostComponent {}

describe('PasswordToggleComponent', () => {
  let fixture: ComponentFixture<HostComponent>;
  let input: HTMLInputElement;
  let button: HTMLButtonElement;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [HostComponent],
      providers: [...provideTestTranslations(), importProvidersFrom(FeatherModule.pick(allIcons))],
    }).compileComponents();
    fixture = TestBed.createComponent(HostComponent);
    fixture.detectChanges();
    input = fixture.nativeElement.querySelector('input');
    button = fixture.nativeElement.querySelector('button');
  });

  const icon = (): string | null => fixture.nativeElement.querySelector('i-feather svg')?.getAttribute('class')?.replace('feather feather-', '') ?? null;

  it('starts hidden with the crossed-out eye (AC-01)', () => {
    expect(input.type).toBe('password');
    expect(icon()).toBe('eye-off');
    expect(button.getAttribute('aria-pressed')).toBe('false');
  });

  it('shows and hides the password on click, keeping the value (AC-02, AC-03)', () => {
    button.click();
    fixture.detectChanges();
    expect(input.type).toBe('text');
    expect(icon()).toBe('eye');
    expect(button.getAttribute('aria-pressed')).toBe('true');
    expect(input.value).toBe('secreto');
    button.click();
    fixture.detectChanges();
    expect(input.type).toBe('password');
    expect(icon()).toBe('eye-off');
  });

  it('is a non-submit button with an accessible name (AC-03)', () => {
    expect(button.type).toBe('button');
    expect(button.getAttribute('aria-label')).toBeTruthy();
  });
});
