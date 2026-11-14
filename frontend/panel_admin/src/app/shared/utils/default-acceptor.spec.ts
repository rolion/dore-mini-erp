import { defaultAcceptor, isMinor } from './default-acceptor';

const TODAY = new Date(2026, 10, 12);

describe('default-acceptor', () => {
  it('detecta al menor de 18 años cumplidos', () => {
    expect(isMinor('2020-06-04', TODAY)).toBeTrue();
    expect(isMinor('2008-11-13', TODAY)).toBeTrue(); // cumple 18 mañana
    expect(isMinor('2008-11-12', TODAY)).toBeFalse(); // cumple 18 hoy
    expect(isMinor('1990-01-01', TODAY)).toBeFalse();
    expect(isMinor(null, TODAY)).toBeFalse();
    expect(isMinor('', TODAY)).toBeFalse();
  });

  it('propone al responsable si el paciente es menor y lo tiene (INV-05)', () => {
    expect(defaultAcceptor('oscar', '2020-06-04', ' rodrigo leon ', TODAY)).toBe('rodrigo leon');
  });

  it('propone al paciente si es mayor, no tiene responsable o no tiene fecha de nacimiento', () => {
    expect(defaultAcceptor('Rosa', '1990-01-01', 'Otra persona', TODAY)).toBe('Rosa');
    expect(defaultAcceptor('oscar', '2020-06-04', '', TODAY)).toBe('oscar');
    expect(defaultAcceptor('oscar', null, 'rodrigo', TODAY)).toBe('oscar');
    expect(defaultAcceptor(' Rosa ', undefined, undefined, TODAY)).toBe('Rosa');
  });
});
