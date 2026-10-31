import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { ButtonsComponent } from './buttons.component';

describe('ButtonsComponent', () => {
  let component: ButtonsComponent;
  let fixture: ComponentFixture<ButtonsComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideTemplateTestServices()],
    imports: [ButtonsComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(ButtonsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('updates template and reactive radio models through native controls', () => {
    const radios = (fixture.nativeElement as HTMLElement).querySelectorAll<HTMLInputElement>('input[type="radio"]');
    radios[1].click();
    fixture.detectChanges();
    expect(component.modelRadio).toBe(2);
    radios[4].click();
    fixture.detectChanges();
    expect(component.radioGroupForm.get('modelRadioForm')?.value).toBe('Middle');
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
