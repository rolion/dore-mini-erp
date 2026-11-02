import { HttpErrorResponse } from '@angular/common/http';
import { TestBed } from '@angular/core/testing';
import { of, throwError } from 'rxjs';
import { DentistryApiService } from '../services/dentistry-api.service';
import { PatientHistoryComponent } from './patient-history.component';
describe('PatientHistoryComponent', () => {
  let api: jasmine.SpyObj<DentistryApiService>;
  beforeEach(async () => {
    api = jasmine.createSpyObj<DentistryApiService>('api', ['history']);
    await TestBed.configureTestingModule({ imports: [PatientHistoryComponent], providers: [{ provide: DentistryApiService, useValue: api }] }).compileComponents();
  });
  it('shows audit author, before/after and server-side pagination', () => {
    api.history.and.returnValue(of({ count: 11, next: '/next', previous: null, results: [{ id: 1, author_id: 1,
      author_name: 'ana', action: 'edit', created_at: '2026-11-02T14:00:00Z', before: { allergies: '' }, after: { allergies: 'Penicilina' } }] }));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1'); fixture.detectChanges();
    expect(fixture.nativeElement.textContent).toContain('ana');
    expect(fixture.nativeElement.textContent).toContain('No informado');
    expect(fixture.nativeElement.textContent).toContain('Penicilina');
    fixture.componentInstance.move(1); expect(api.history).toHaveBeenCalledWith('c-1', true, 2);
  });
  it('clears audit rows on a permission error and offers retry', () => {
    api.history.and.returnValue(throwError(() => new HttpErrorResponse({ status: 403 })));
    const fixture = TestBed.createComponent(PatientHistoryComponent);
    fixture.componentRef.setInput('patientId', 'c-1'); fixture.detectChanges();
    expect(fixture.componentInstance.rows).toEqual([]);
    expect(fixture.nativeElement.textContent).toContain('No tienes permiso');
    expect(fixture.nativeElement.textContent).toContain('Reintentar');
  });
});
