import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { AuthService, User } from '@core';
import { SidebarComponent } from './sidebar.component';
import { RouteInfo } from './sidebar.metadata';
describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;
  let session: User | null;
  beforeEach(waitForAsync(() => {
    session = null;
    TestBed.configureTestingModule({
    imports: [SidebarComponent],
    providers: [
      provideRouter([]),
      provideHttpClient(),
      provideHttpClientTesting(),
      provideTranslateService(),
      importProvidersFrom(FeatherModule.pick(allIcons)),
      { provide: AuthService, useValue: { get currentUserValue() { return session; } } },
    ]
}).compileComponents();
  }));
  const create = (user: User | null = null) => {
    session = user;
    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  };
  beforeEach(() => create());
  it('should create', () => {
    expect(component).toBeTruthy();
  });

  describe('user panel (AC-02, AC-03)', () => {
    it('shows initials, full name and company of the session', () => {
      create({
        id: 1, username: 'maria', firstName: 'María', lastName: 'Quispe', token: 't',
        company: { id: 'c-1', name: 'Cuñapés SRL' },
      });
      const el: HTMLElement = fixture.nativeElement;
      expect(el.querySelector('.user-panel img')).toBeNull();
      expect(el.querySelector('.user-panel figure.avatar')?.getAttribute('data-initial')).toBe('MQ');
      expect(el.querySelector('.sidebar-userpic-name')?.textContent?.trim()).toBe('María Quispe');
      expect(el.querySelector('.profile-usertitle-job')?.textContent?.trim()).toBe('Cuñapés SRL');
      expect(el.textContent).not.toContain('Emily');
    });

    it('omits the company line for old sessions without company', () => {
      create({ id: 1, username: 'ana', firstName: '', lastName: '', token: 't' });
      const el: HTMLElement = fixture.nativeElement;
      expect(el.querySelector('.sidebar-userpic-name')?.textContent?.trim()).toBe('ana');
      expect(el.querySelector('.user-panel figure.avatar')?.getAttribute('data-initial')).toBe('A');
      expect(el.querySelector('.profile-usertitle-job')).toBeNull();
    });
  });

  describe('linkActiveOptions (AC-10, un solo ítem resaltado)', () => {
    const item = (path: string): RouteInfo => ({
      path,
      title: '',
      iconType: '',
      icon: '',
      class: '',
      groupTitle: false,
      badge: '',
      badgeClass: '',
      submenu: [],
    });
    const expenses = item('/pocketbiz/expenses');
    const categories = item('/pocketbiz/expenses/categories');
    const products = item('/pocketbiz/catalog/products');

    it('requires an exact match when a sibling extends the path', () => {
      expect(component.linkActiveOptions(expenses, [expenses, categories])).toEqual({ exact: true });
    });

    it('keeps prefix matching for the extending item and for unrelated siblings', () => {
      expect(component.linkActiveOptions(categories, [expenses, categories])).toEqual({ exact: false });
      expect(component.linkActiveOptions(products, [products])).toEqual({ exact: false });
    });
  });

  describe('menu by enabled modules (AC-04, AC-05, AC-08)', () => {
    const base = { iconType: '', icon: '', class: '', groupTitle: false, badge: '', badgeClass: '', submenu: [] };
    const moduleDto = (key: string, enabled: boolean) => ({
      key, name: key, description: '', is_base: false, enabled, requires: [], optional: [], missing_requires: [],
    });

    const flush = (enabled: Record<string, boolean>) => {
      const http = TestBed.inject(HttpTestingController);
      http.expectOne('assets/data/routes.json').flush({
        routes: [
          { ...base, path: '/customers', title: 'Clientes', module: 'customers' },
          { ...base, path: '/inventory', title: 'Inventario', module: 'inventory' },
          { ...base, path: '/settings/modules', title: 'Módulos' },
        ],
      });
      http.expectOne((req) => req.url.endsWith('/modules/')).flush(
        Object.entries(enabled).map(([key, on]) => moduleDto(key, on)),
      );
      fixture.detectChanges();
    };

    it('shows only items of enabled modules plus items without module', () => {
      create({ id: 1, username: 'ana', firstName: '', lastName: '', token: 't' });
      flush({ customers: true, inventory: true });
      expect(component.sidebarItems.map((item) => item.path)).toEqual(['/customers', '/inventory', '/settings/modules']);
    });

    it('hides the menu of a module that is not enabled for the company', () => {
      create({ id: 1, username: 'ana', firstName: '', lastName: '', token: 't' });
      flush({ customers: true, inventory: false });
      expect(component.sidebarItems.map((item) => item.path)).toEqual(['/customers', '/settings/modules']);
    });
  });

  it('renders the main and the collapsed PocketBiz logos without the old brand text (AC-03)', () => {
    const el: HTMLElement = fixture.nativeElement;
    const sources = Array.from(
      el.querySelectorAll<HTMLImageElement>('.sidebar-brand img'),
    ).map((img) => img.getAttribute('src'));
    expect(sources).toEqual(['assets/images/main-logo.png', 'assets/images/simple-logo.png']);
    expect(el.querySelector('.sidebar-brand .logo-name')).toBeNull();
  });
});
