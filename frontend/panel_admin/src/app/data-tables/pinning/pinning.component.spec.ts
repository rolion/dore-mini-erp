import { ComponentFixture, TestBed } from '@angular/core/testing';

import { PinningComponent } from './pinning.component';

describe('PinningComponent', () => {
  let component: PinningComponent;
  let fixture: ComponentFixture<PinningComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
    imports: [PinningComponent]
})
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(PinningComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
