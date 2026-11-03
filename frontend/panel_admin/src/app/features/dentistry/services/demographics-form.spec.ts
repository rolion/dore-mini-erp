import { FormControl, FormGroup } from '@angular/forms';
import { demographicsValidator, minorAt } from './demographics-form';
describe('Administrative demographics', () => {
  it('distinguishes unknown age and the exact 18th birthday', () => {
    expect(minorAt('', new Date(2026, 10, 2))).toBeFalse();
    expect(minorAt('2008-11-03', new Date(2026, 10, 2))).toBeTrue();
    expect(minorAt('2008-11-02', new Date(2026, 10, 2))).toBeFalse();
    expect(minorAt('2008-02-29', new Date(2026, 1, 28))).toBeTrue();
    expect(minorAt('2008-02-29', new Date(2026, 2, 1))).toBeFalse();
  });
  it('requires both responsible fields for known minors and rejects future births', () => {
    const form = new FormGroup({ birth_date: new FormControl('2099-01-01'), responsible_name: new FormControl(''),
      responsible_phone: new FormControl('') }, demographicsValidator);
    expect(form.hasError('futureBirth')).toBeTrue();
    expect(form.hasError('responsibleName')).toBeTrue();
    expect(form.hasError('responsiblePhone')).toBeTrue();
    form.setValue({ birth_date: '', responsible_name: '', responsible_phone: '' });
    expect(form.valid).toBeTrue();
    form.patchValue({ responsible_name: 'Tutor' });
    expect(form.hasError('responsiblePhone')).toBeTrue();
  });
});
