import { provideTestTranslations } from '../../core/i18n/testing';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { BasicDatatableComponent } from './basic-datatable.component';

describe('BasicDatatableComponent', () => {
  let component: BasicDatatableComponent;
  let fixture: ComponentFixture<BasicDatatableComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [...provideTestTranslations(), provideTemplateTestServices()],
    imports: [BasicDatatableComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(BasicDatatableComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
