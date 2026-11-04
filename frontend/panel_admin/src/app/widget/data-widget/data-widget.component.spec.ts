import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DataWidgetComponent } from './data-widget.component';

describe('DataWidgetComponent', () => {
  let component: DataWidgetComponent;
  let fixture: ComponentFixture<DataWidgetComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [DataWidgetComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(DataWidgetComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
