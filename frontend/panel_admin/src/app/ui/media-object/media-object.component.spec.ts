import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { MediaObjectComponent } from './media-object.component';

describe('MediaObjectComponent', () => {
  let component: MediaObjectComponent;
  let fixture: ComponentFixture<MediaObjectComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [MediaObjectComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(MediaObjectComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
