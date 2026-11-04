// Verifica que toda clave usada en plantillas y en TypeScript exista en los catálogos es/en/pt
// y que ninguna clave del catálogo quede sin usar por error de tipeo (solo informa las faltantes).
// Uso: node tools/check-i18n-keys.mjs
import { readdirSync, readFileSync, statSync } from 'node:fs';
import { join } from 'node:path';

const root = new URL('../src/app/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const i18n = new URL('../src/assets/i18n/', import.meta.url).pathname.replace(/^\/([A-Za-z]:)/, '$1');
const catalogs = Object.fromEntries(['es', 'en', 'pt'].map((l) => [l, JSON.parse(readFileSync(join(i18n, l + '.json'), 'utf8'))]));

const has = (cat, key) => key.split('.').reduce((n, p) => (n && typeof n === 'object' ? n[p] : undefined), cat) !== undefined;
const files = [];
(function walk(dir) {
  for (const f of readdirSync(dir)) {
    const p = join(dir, f);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(html|ts)$/.test(f) && !f.endsWith('.spec.ts')) files.push(p);
  }
})(root);

const used = new Map();
for (const file of files) {
  const src = readFileSync(file, 'utf8');
  for (const m of src.matchAll(/'([A-Z][A-Z0-9_-]*(?:\.[A-Z0-9_-]+)+)'\s*\|\s*translate|\btr\(\s*'([A-Z][A-Z0-9_-]*(?:\.[A-Z0-9_-]+)+)'/g)) {
    const key = m[1] ?? m[2];
    if (!used.has(key)) used.set(key, file);
  }
}
let missing = 0;
for (const [key, file] of used) {
  for (const l of Object.keys(catalogs)) {
    if (!has(catalogs[l], key)) {
      console.error(`Falta ${l}: ${key}  (${file.replace(root, '')})`);
      missing++;
    }
  }
}
console.log(`${used.size} claves usadas, ${missing} faltantes`);
process.exit(missing ? 1 : 0);
