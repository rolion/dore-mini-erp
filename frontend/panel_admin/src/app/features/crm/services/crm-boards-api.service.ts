import { HttpClient, HttpErrorResponse, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable, catchError, map, throwError } from 'rxjs';
import { environment } from '../../../../environments/environment';
import { CrmApiError, CrmBoard, CrmBoardDto, genericErrorMessage, networkErrorMessage } from '../models/board';

export function toBoard(dto: CrmBoardDto): CrmBoard {
  return {
    id: dto.id,
    name: dto.name,
    isActive: dto.is_active,
    stages: dto.stages.map((s) => ({
      id: s.id, name: s.name, position: s.position, isActive: s.is_active, cardCount: s.card_count,
    })),
  };
}

function first(value: unknown): string | undefined {
  return Array.isArray(value) && value.length ? value.map(String).join(' ') : undefined;
}

export function toApiError(error: HttpErrorResponse): CrmApiError {
  if (error.status === 0) {
    return new CrmApiError(networkErrorMessage(), 0);
  }
  const body = (error.error && typeof error.error === 'object' ? error.error : {}) as Record<string, unknown>;
  const detail = typeof body['detail'] === 'string' ? body['detail'] : '';
  const code = typeof body['code'] === 'string' ? body['code'] : null;
  const count = typeof body['card_count'] === 'number' ? body['card_count'] : 0;
  if (error.status === 400) {
    return new CrmApiError(genericErrorMessage(), 400, {
      name: first(body['name']), targetStageId: first(body['target_stage_id']),
    });
  }
  return new CrmApiError(detail || genericErrorMessage(), error.status, {}, code, count);
}

@Injectable({ providedIn: 'root' })
export class CrmBoardsApiService {
  private http = inject(HttpClient);
  private readonly baseUrl = `${environment.apiUrl}/crm/boards/`;

  list(active?: boolean): Observable<CrmBoard[]> {
    let params = new HttpParams();
    if (active !== undefined) params = params.set('active', String(active));
    return this.http.get<CrmBoardDto[]>(this.baseUrl, { params }).pipe(
      map((boards) => boards.map(toBoard)),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }

  create(name: string): Observable<CrmBoard> {
    return this.board(this.http.post<CrmBoardDto>(this.baseUrl, { name }));
  }

  rename(boardId: string, name: string): Observable<CrmBoard> {
    return this.board(this.http.patch<CrmBoardDto>(`${this.baseUrl}${boardId}/`, { name }));
  }

  archive(boardId: string): Observable<CrmBoard> {
    return this.board(this.http.post<CrmBoardDto>(`${this.baseUrl}${boardId}/archive/`, {}));
  }

  reactivate(boardId: string): Observable<CrmBoard> {
    return this.board(this.http.post<CrmBoardDto>(`${this.baseUrl}${boardId}/reactivate/`, {}));
  }

  addStage(boardId: string, name: string): Observable<CrmBoard> {
    return this.board(this.http.post<CrmBoardDto>(`${this.baseUrl}${boardId}/stages/`, { name }));
  }

  renameStage(boardId: string, stageId: string, name: string): Observable<CrmBoard> {
    return this.board(this.http.patch<CrmBoardDto>(`${this.baseUrl}${boardId}/stages/${stageId}/`, { name }));
  }

  reorderStages(boardId: string, stageIds: string[]): Observable<CrmBoard> {
    return this.board(this.http.put<CrmBoardDto>(`${this.baseUrl}${boardId}/stages/order/`, { stage_ids: stageIds }));
  }

  archiveStage(boardId: string, stageId: string, targetStageId?: string): Observable<CrmBoard> {
    const body = targetStageId ? { target_stage_id: targetStageId } : {};
    return this.board(this.http.post<CrmBoardDto>(`${this.baseUrl}${boardId}/stages/${stageId}/archive/`, body));
  }

  private board(request: Observable<CrmBoardDto>): Observable<CrmBoard> {
    return request.pipe(
      map(toBoard),
      catchError((err: HttpErrorResponse) => throwError(() => toApiError(err))),
    );
  }
}
