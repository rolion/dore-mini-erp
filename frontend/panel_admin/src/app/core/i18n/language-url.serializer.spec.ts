import { TestBed } from '@angular/core/testing';
import { UrlSerializer } from '@angular/router';
import { LanguageState } from './language-state';
import { LANGUAGE_URL_SERIALIZER_PROVIDER } from './language-url.serializer';
import { addLanguagePrefix, languageFromUrl, stripLanguagePrefix } from './language.config';

describe('LanguageUrlSerializer', () => {
  let serializer: UrlSerializer;
  let state: LanguageState;

  beforeEach(() => {
    TestBed.configureTestingModule({ providers: [LANGUAGE_URL_SERIALIZER_PROVIDER] });
    serializer = TestBed.inject(UrlSerializer);
    state = TestBed.inject(LanguageState);
  });

  it('strips the prefix when parsing and sets the active language', () => {
    const tree = serializer.parse('/en/pocketbiz/login?x=1#a');
    expect(state.active).toBe('en');
    expect(tree.root.children['primary'].segments.map((s) => s.path)).toEqual(['pocketbiz', 'login']);
    expect(tree.queryParams['x']).toBe('1');
    expect(tree.fragment).toBe('a');
  });

  it('adds the active prefix when serializing', () => {
    state.set('pt');
    const tree = serializer.parse('/pocketbiz/sales/orders/12?x=1#a');
    expect(serializer.serialize(tree)).toBe('/pt/pocketbiz/sales/orders/12?x=1#a');
  });

  it('serializes the root as the bare prefix', () => {
    expect(serializer.serialize(serializer.parse('/'))).toBe('/es');
    expect(serializer.serialize(serializer.parse('/pt'))).toBe('/pt');
  });

  it('keeps unprefixed URLs working (old bookmarks) in the current language', () => {
    serializer.parse('/pocketbiz/login');
    expect(state.active).toBe('es');
  });

  it('does not treat unsupported prefixes as languages', () => {
    const tree = serializer.parse('/fr/pocketbiz/login');
    expect(state.active).toBe('es');
    expect(tree.root.children['primary'].segments[0].path).toBe('fr');
  });

  it('never prefixes /api or /admin', () => {
    expect(addLanguagePrefix('/api/health/', 'en')).toBe('/api/health/');
    expect(addLanguagePrefix('/admin/', 'en')).toBe('/admin/');
  });

  it('helpers handle prefix boundaries', () => {
    expect(languageFromUrl('/english')).toBeNull();
    expect(languageFromUrl('/en')).toBe('en');
    expect(stripLanguagePrefix('/en?x=1')).toBe('/?x=1');
    expect(stripLanguagePrefix('/en')).toBe('/');
  });
});
