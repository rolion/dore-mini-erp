import { provideTemplateTestServices } from '../../../../testing/template-test.providers';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { Second2Component } from './second2.component';

describe('Second2Component', () => {
  let component: Second2Component;
  let fixture: ComponentFixture<Second2Component>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      providers: [provideTemplateTestServices()],
    imports: [Second2Component]
})
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(Second2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
