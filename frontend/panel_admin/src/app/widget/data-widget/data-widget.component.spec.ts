import { ComponentFixture, TestBed } from '@angular/core/testing';

import { DataWidgetComponent } from './data-widget.component';

describe('DataWidgetComponent', () => {
  let component: DataWidgetComponent;
  let fixture: ComponentFixture<DataWidgetComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
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
