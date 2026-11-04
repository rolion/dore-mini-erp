import { provideTestTranslations } from '../../core/i18n/testing';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';
import { RightSidebarComponent } from './right-sidebar.component';
describe('RightSidebarComponent', () => {
  let component: RightSidebarComponent;
  let fixture: ComponentFixture<RightSidebarComponent>;
  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({ providers: [...provideTestTranslations()],
    imports: [RightSidebarComponent]
}).compileComponents();
  }));
  beforeEach(() => {
    fixture = TestBed.createComponent(RightSidebarComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });
  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
