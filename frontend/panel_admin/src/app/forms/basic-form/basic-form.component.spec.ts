import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BasicFormComponent } from './basic-form.component';

describe('BasicFormComponent', () => {
  let component: BasicFormComponent;
  let fixture: ComponentFixture<BasicFormComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [BasicFormComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BasicFormComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
