import { provideHttpClient } from '@angular/common/http';
import { provideHttpClientTesting } from '@angular/common/http/testing';
import { importProvidersFrom } from '@angular/core';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { provideRouter } from '@angular/router';
import { FeatherModule } from 'angular-feather';
import { allIcons } from 'angular-feather/icons';
import { provideTranslateService } from '@ngx-translate/core';
import { SidebarComponent } from './sidebar.component';
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

  it('renders the main and the collapsed PocketBiz logos without the old brand text (AC-03)', () => {
    const el: HTMLElement = fixture.nativeElement;
    const sources = Array.from(
      el.querySelectorAll<HTMLImageElement>('.sidebar-brand img'),
    ).map((img) => img.getAttribute('src'));
    expect(sources).toEqual(['assets/images/main-logo.png', 'assets/images/simple-logo.png']);
    expect(el.querySelector('.sidebar-brand .logo-name')).toBeNull();
  });
});
