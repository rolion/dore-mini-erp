import { ComponentFixture, TestBed } from '@angular/core/testing';

import { NgxchartComponent } from './ngxchart.component';

describe('NgxchartComponent', () => {
  let component: NgxchartComponent;
  let fixture: ComponentFixture<NgxchartComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
    imports: [NgxchartComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(NgxchartComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
