import { ComponentFixture, TestBed } from '@angular/core/testing';

import { AdvanceControlComponent } from './advance-control.component';

describe('AdvanceControlComponent', () => {
  let component: AdvanceControlComponent;
  let fixture: ComponentFixture<AdvanceControlComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
    imports: [AdvanceControlComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(AdvanceControlComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
