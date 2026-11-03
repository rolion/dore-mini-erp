import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { AbsencePayload, Shift, ShiftPayload, Week } from '../models/agenda';

@Injectable({ providedIn: 'root' })
export class AgendaApiService {
  private http = inject(HttpClient);

  private base(professionalId: string): string {
    return `${environment.apiUrl}/agenda/${professionalId}/`;
  }

  week(professionalId: string, start: string): Observable<Week> {
    return this.http.get<Week>(this.base(professionalId) + 'week/', { params: { start } });
  }

  saveShift(professionalId: string, body: ShiftPayload, shiftId?: number): Observable<Shift> {
    const url = this.base(professionalId) + 'shifts/';
    return shiftId ? this.http.put<Shift>(`${url}${shiftId}/`, body) : this.http.post<Shift>(url, body);
  }

  saveAbsence(professionalId: string, body: AbsencePayload): Observable<unknown> {
    return this.http.post(this.base(professionalId) + 'absences/', body);
  }
}
