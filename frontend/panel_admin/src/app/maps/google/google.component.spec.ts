import { CUSTOM_ELEMENTS_SCHEMA } from '@angular/core';
import { GoogleMapsModule } from '@angular/google-maps';
import { provideTemplateTestServices } from '../../../testing/template-test.providers';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { GoogleComponent } from './google.component';

describe('GoogleComponent', () => {
  let component: GoogleComponent;
  let fixture: ComponentFixture<GoogleComponent>;

  beforeEach(async () => {
    await TestBed.configureTestingModule({
      providers: [provideTemplateTestServices()],
    imports: [GoogleComponent]
})
    .overrideComponent(GoogleComponent, {
      remove: { imports: [GoogleMapsModule] },
      add: { schemas: [CUSTOM_ELEMENTS_SCHEMA] },
    })
    .compileComponents();
  });

  beforeEach(() => {
    fixture = TestBed.createComponent(GoogleComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('creates the page shell without loading the external Google Maps SDK', () => {
    expect(component).toBeTruthy();
    expect((fixture.nativeElement as HTMLElement).querySelector('google-map')).not.toBeNull();
  });
});
