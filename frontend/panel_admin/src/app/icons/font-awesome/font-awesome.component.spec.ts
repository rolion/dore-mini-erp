import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { FontAwesomeComponent } from './font-awesome.component';

describe('FontAwesomeComponent', () => {
  let component: FontAwesomeComponent;
  let fixture: ComponentFixture<FontAwesomeComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [FontAwesomeComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(FontAwesomeComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
