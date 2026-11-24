import { CrmBoard, CrmStage } from '../models/board';

export function makeStage(overrides: Partial<CrmStage> = {}): CrmStage {
  return { id: 's-1', name: 'Nuevo', position: 1, isActive: true, cardCount: 0, ...overrides };
}

export function makeBoard(overrides: Partial<CrmBoard> = {}): CrmBoard {
  return { id: 'b-1', name: 'Ventas', isActive: true, stages: [], ...overrides };
}
