import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { of } from 'rxjs';
import { provideTranslateService } from '@ngx-translate/core';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { AuthService, User } from '@core';
import { HeaderComponent } from './header.component';

describe('HeaderComponent', () => {
  let component: HeaderComponent;
  let fixture: ComponentFixture<HeaderComponent>;
  let session: User | null;
  let logoutCalls: number;

  beforeEach(waitForAsync(() => {
    session = null;
    logoutCalls = 0;
    TestBed.configureTestingModule({
      imports: [HeaderComponent],
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        provideTranslateService(),
        importProvidersFrom(FeatherModule.pick(allIcons)),
        {
          provide: AuthService,
          useValue: {
            get currentUserValue() { return session; },
            logout: () => { logoutCalls += 1; return of({ success: false }); },
          },
        },
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

  it('shows an initials avatar in the user button instead of an image (AC-05, AC-07)', () => {
    session = {
      id: 1, username: 'maria', firstName: 'María', lastName: 'Quispe', token: 't',
      company: { id: 'c-1', name: 'Cuñapés SRL' },
    };
    create();
    const toggle = (fixture.nativeElement as HTMLElement).querySelector('.user-toggle') as HTMLElement;
    const avatar = toggle.querySelector('figure.avatar') as HTMLElement;
    expect(avatar.getAttribute('data-initial')).toBe('MQ');
    expect(avatar.getAttribute('aria-label')).toBe('María Quispe');
    expect(toggle.querySelector('img')).toBeNull();
  });

  it('has no search, messages nor notifications (AC-04)', () => {
    create();
    const el: HTMLElement = fixture.nativeElement;
    expect(el.querySelector('.search-element')).toBeNull();
    expect(el.querySelector('input[type="search"]')).toBeNull();
    expect(el.querySelector('i-feather[name="mail"]')).toBeNull();
    expect(el.querySelector('i-feather[name="bell"]')).toBeNull();
  });

  it('user menu only has name, company and logout (AC-06)', () => {
    session = {
      id: 1, username: 'maria', firstName: 'María', lastName: 'Quispe', token: 't',
      company: { id: 'c-1', name: 'Cuñapés SRL' },
    };
    create();
    const menu = (fixture.nativeElement as HTMLElement).querySelector('.user-toggle')
      ?.parentElement?.querySelector('.dropdown-menu') as HTMLElement;
    const links = Array.from(menu.querySelectorAll('a')).map((a) => a.textContent?.trim());
    expect(links).toEqual(['Logout']);
    expect(menu.querySelector('.dropdown-title')?.textContent?.trim()).toBe('María Quispe');
    expect(menu.querySelector('.company-name')?.textContent?.trim()).toBe('Cuñapés SRL');
  });

  it('falls back to the username and hides the company for old sessions (AC-15, EDGE-03)', () => {
    session = { id: 1, username: 'ana', firstName: '', lastName: '', token: 't' };
    create();
    expect(component.userDisplayName).toBe('ana');
    expect(component.companyName).toBe('');
    expect((fixture.nativeElement as HTMLElement).querySelector('.company-name')).toBeNull();
  });

  it('logout item closes the session (AC-06)', () => {
    create();
    const logout = (fixture.nativeElement as HTMLElement).querySelector('.logout-item') as HTMLElement;
    logout.click();
    expect(logoutCalls).toBe(1);
  });
});
