import en from '../../../assets/i18n/en.json';
import es from '../../../assets/i18n/es.json';
import pt from '../../../assets/i18n/pt.json';

interface Tree {
  [key: string]: string | Tree;
}

function flatten(tree: Tree, prefix = ''): Record<string, string> {
  const out: Record<string, string> = {};
  for (const [key, value] of Object.entries(tree)) {
    if (typeof value === 'string') {
      out[prefix + key] = value;
    } else {
      Object.assign(out, flatten(value, `${prefix}${key}.`));
    }
  }
  return out;
}

const placeholders = (text: string): string[] =>
  (text.match(/\{\{\s*\w+\s*\}\}/g) ?? []).map((p) => p.replace(/\s/g, '')).sort();

describe('translation catalogs', () => {
  const catalogs = { es: flatten(es as Tree), en: flatten(en as Tree), pt: flatten(pt as Tree) };

  it('have exactly the same keys in es, en and pt (INV-03)', () => {
    const keys = Object.keys(catalogs.es).sort();
    expect(Object.keys(catalogs.en).sort()).toEqual(keys);
    expect(Object.keys(catalogs.pt).sort()).toEqual(keys);
  });

  it('have no empty values and the same interpolations', () => {
    for (const [key, text] of Object.entries(catalogs.es)) {
      expect(text.trim()).not.toBe('', `es ${key}`);
      for (const lang of ['en', 'pt'] as const) {
        const other = catalogs[lang][key];
        expect((other ?? '').trim()).not.toBe('', `${lang} ${key}`);
        expect(placeholders(other ?? '')).toEqual(placeholders(text), `${lang} ${key}`);
      }
    }
  });
});
