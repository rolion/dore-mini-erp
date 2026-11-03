import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed, waitForAsync } from '@angular/core/testing';

import { First2Component } from './first2.component';

describe('First2Component', () => {
  let component: First2Component;
  let fixture: ComponentFixture<First2Component>;

  beforeEach(waitForAsync(() => {
    TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [First2Component]
})
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(First2Component);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
