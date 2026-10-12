import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { SidebarComponent } from './sidebar.component';
import { RouteInfo } from './sidebar.metadata';
describe('SidebarComponent', () => {
  let component: SidebarComponent;
  let fixture: ComponentFixture<SidebarComponent>;
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
    imports: [SidebarComponent],
    providers: [
      provideRouter([]),
      provideHttpClient(),
      provideHttpClientTesting(),
      provideTranslateService(),
      importProvidersFrom(FeatherModule.pick(allIcons)),
    ]
}).compileComponents();
  }));
  beforeEach(() => {
    fixture = TestBed.createComponent(SidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
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
    const expenses = item('/expenses');
    const categories = item('/expenses/categories');
    const products = item('/catalog/products');

    it('requires an exact match when a sibling extends the path', () => {
      expect(component.linkActiveOptions(expenses, [expenses, categories])).toEqual({ exact: true });
    });

    it('keeps prefix matching for the extending item and for unrelated siblings', () => {
      expect(component.linkActiveOptions(categories, [expenses, categories])).toEqual({ exact: false });
      expect(component.linkActiveOptions(products, [products])).toEqual({ exact: false });
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
