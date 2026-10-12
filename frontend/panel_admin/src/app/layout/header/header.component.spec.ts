import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { provideTranslateService } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { AuthService, User } from '@core';
import { HeaderComponent } from './header.component';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;
  let session: User | null;

  beforeEach(waitForAsync(() => {
    session = null;
    TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideTranslateService(),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        { provide: AuthService, useValue: { get currentUserValue() { return session; } } },
      ],
    }).compileComponents();
  }));

  const create = () => {
    fixture = TestBed.createComponent(HeaderComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };

  it('should create', () => {
    create();
    expect(component).toBeTruthy();
  });

  it('shows the full name and the company of the session (AC-15)', () => {
    session = {
      id: 1, username: 'maria', firstName: 'María', lastName: 'Quispe', token: 't',
      role: 'admin', company: { id: 'c-1', name: 'Cuñapés SRL' },
    };
    create();
    expect(component.userDisplayName).toBe('María Quispe');
    expect(component.companyName).toBe('Cuñapés SRL');
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.dropdown-title')?.textContent?.trim()).toBe('María Quispe');
    expect(el.querySelector('.company-name')?.textContent?.trim()).toBe('Cuñapés SRL');
  });

  it('falls back to the username and hides the company for old sessions (AC-15, EDGE-03)', () => {
    session = { id: 1, username: 'ana', firstName: '', lastName: '', token: 't' };
    create();
    expect(component.userDisplayName).toBe('ana');
    expect(component.companyName).toBe('');
    expect((fixture.nativeElement as HTMLElement).querySelector('.company-name')).toBeNull();
  });
});
