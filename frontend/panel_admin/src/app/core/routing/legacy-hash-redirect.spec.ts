import { LocationStrategy } from '@angular/common';
import { appConfig } from '../../app.config';
import { legacyHashTarget, redirectLegacyHash } from './legacy-hash-redirect';

describe('Compatibilidad con URLs con hash (AC-18, EDGE-07)', () => {
  describe('legacyHashTarget', () => {
    it('turns #/<ruta> into /<ruta>, keeping subroute and query', () => {
      expect(legacyHashTarget('#/authentication/signin')).toBe('/authentication/signin');
      expect(legacyHashTarget('#/sales/orders?status=NEW')).toBe('/sales/orders?status=NEW');
      expect(legacyHashTarget('#/pocketbiz/login')).toBe('/pocketbiz/login');
    });

    it('ignores empty hashes, the bare root and in-page anchors (EDGE-07)', () => {
      for (const hash of ['', '#', '#/', '#seccion', '#que-puedes-controlar', 'authentication']) {
        expect(legacyHashTarget(hash)).withContext(hash).toBeNull();
      }
    });
  });

  describe('redirectLegacyHash', () => {
    const fakeWindow = (hash: string) => {
      const replaceState = jasmine.createSpy('replaceState');
      const win = {
        location: { hash } as Location,
        history: { replaceState } as unknown as History,
      };
      return { win, replaceState };
    };

    it('replaces the history entry with the clean route (AC-18)', () => {
      const { win, replaceState } = fakeWindow('#/dashboard/main?x=1');

      expect(redirectLegacyHash(win)).toBeTrue();
      expect(replaceState).toHaveBeenCalledOnceWith(null, '', '/dashboard/main?x=1');
    });

    it('does nothing when the hash is not a route (EDGE-07)', () => {
      for (const hash of ['', '#/', '#seccion']) {
        const { win, replaceState } = fakeWindow(hash);
        expect(redirectLegacyHash(win)).withContext(hash).toBeFalse();
        expect(replaceState).not.toHaveBeenCalled();
      }
    });
  });

  describe('estrategia de ubicación', () => {
    it('does not provide HashLocationStrategy: URLs have no "#" (AC-18)', () => {
      const overrides = appConfig.providers.filter(
        (provider) =>
          typeof provider === 'object' &&
          provider !== null &&
          'provide' in provider &&
          (provider as { provide: unknown }).provide === LocationStrategy
      );
      expect(overrides.length).toBe(0);
    });
  });
});
