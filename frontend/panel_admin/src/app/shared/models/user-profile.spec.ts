import { userFullName, userInitials } from './user-profile';

describe('user-profile', () => {
  describe('userInitials (AC-01)', () => {
    it('uses the first letters of first and last name in uppercase', () => {
      expect(userInitials({ firstName: 'María', lastName: 'Quispe' })).toBe('MQ');
      expect(userInitials({ firstName: 'maría', lastName: ' quispe ' })).toBe('MQ');
    });

    it('uses a single letter when only one of them exists', () => {
      expect(userInitials({ firstName: 'Ana', lastName: '' })).toBe('A');
      expect(userInitials({ firstName: '', lastName: 'Quispe' })).toBe('Q');
    });

    it('falls back to the username and then to "?"', () => {
      expect(userInitials({ firstName: '', lastName: '', username: 'ana' })).toBe('A');
      expect(userInitials({ firstName: ' ', lastName: ' ', username: ' ' })).toBe('?');
      expect(userInitials(null)).toBe('?');
    });
  });

  describe('userFullName', () => {
    it('joins first and last name, trimmed', () => {
      expect(userFullName({ firstName: 'María ', lastName: 'Quispe' })).toBe('María Quispe');
    });

    it('falls back to the username and is empty without session', () => {
      expect(userFullName({ firstName: '', lastName: '', username: 'ana' })).toBe('ana');
      expect(userFullName(null)).toBe('');
    });
  });
});
