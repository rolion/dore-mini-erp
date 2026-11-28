import { provideTestTranslations } from '../../../core/i18n/testing';
import { TestBed } from '@angular/core/testing';
import { makeCatalog } from '../testing/odontogram-fixtures';
import {
  archRows, conditionName, findingLabel, flattenErrors, isAnterior, isValidPiece, pieceAriaLabel, pieceKind, validSurfaces,
} from './odontogram-utils';

describe('odontogram utils (INV-01…INV-03)', () => {
  const teeth = makeCatalog().teeth;
  beforeEach(() => TestBed.configureTestingModule({ providers: provideTestTranslations() }));

  it('validates FDI pieces by dentition', () => {
    expect(isValidPiece(16, 'permanent', teeth)).toBe(true);
    expect(isValidPiece(19, 'permanent', teeth)).toBe(false);
    expect(isValidPiece(54, 'permanent', teeth)).toBe(false);
    expect(isValidPiece(16, 'temporary', teeth)).toBe(false);
    expect(isValidPiece(54, 'mixed', teeth) && isValidPiece(16, 'mixed', teeth)).toBe(true);
    expect(isValidPiece(56, 'mixed', teeth)).toBe(false);
  });

  it('classifies pieces', () => {
    expect([pieceKind(11), pieceKind(13), pieceKind(14), pieceKind(16), pieceKind(54), pieceKind(55)])
      .toEqual(['incisor', 'canine', 'premolar', 'molar', 'molar', 'molar']);
    expect(isAnterior(23)).toBe(true);
    expect(isAnterior(26)).toBe(false);
  });

  it('allows incisal only on anterior, occlusal only on posterior and palatal/lingual by arch', () => {
    expect(validSurfaces(11)).toEqual(['M', 'D', 'V', 'I', 'P']);
    expect(validSurfaces(46)).toEqual(['M', 'D', 'V', 'O', 'L']);
    expect(validSurfaces(54)).toEqual(['M', 'D', 'V', 'O', 'P']);
    expect(validSurfaces(33)).toEqual(['M', 'D', 'V', 'I', 'L']);
  });

  it('builds arch rows per dentition', () => {
    const permanent = archRows('permanent', teeth);
    expect(permanent.map(row => row.id)).toEqual(['upper-permanent', 'lower-permanent']);
    expect(permanent[0].pieces.slice(0, 2)).toEqual([18, 17]);
    expect(permanent[0].pieces.slice(8, 10)).toEqual([21, 22]);
    expect(permanent[1].pieces.length).toBe(16);
    expect(archRows('temporary', teeth)[0].pieces).toEqual([55, 54, 53, 52, 51, 61, 62, 63, 64, 65]);
    expect(archRows('mixed', teeth).map(row => row.id)).toEqual(['upper-permanent', 'upper-temporary', 'lower-temporary', 'lower-permanent']);
  });

  it('labels findings and pieces with text, not only color', () => {
    const catalog = makeCatalog();
    expect(conditionName(catalog, 'caries')).toBe('Caries');
    expect(conditionName(catalog, 'unknown')).toBe('unknown');
    expect(findingLabel(catalog, { piece: 16, surfaces: ['O', 'M'], condition: 'caries', diagnosis: '', notes: '' })).toBe('Caries (O, M)');
    expect(pieceAriaLabel(catalog, 16, [])).toContain('Sin evaluar');
    expect(pieceAriaLabel(catalog, 16, [{ piece: 16, surfaces: [], condition: 'crown', diagnosis: '', notes: '' }])).toContain('Corona');
  });

  it('flattens nested server errors', () => {
    expect(flattenErrors({ findings: [{ piece: ['Pieza inválida.'] }, {}], clinical_date: ['Requerida.'] }))
      .toEqual(['piece: Pieza inválida.', 'clinical_date: Requerida.']);
  });
});
