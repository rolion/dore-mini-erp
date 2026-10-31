const assert = require('node:assert/strict');
const { test } = require('node:test');
const match = require('./index.cjs');

test('legacy callable API preserves file inclusion/exclusion semantics', () => {
  assert.equal(match('src/app/app.component.spec.ts', '**/*.spec.ts'), true);
  assert.equal(match('src/app/app.component.ts', '**/*.spec.ts'), false);
  assert.equal(match('.hidden.ts', '*.ts'), false);
  assert.equal(match('.hidden.ts', '*.ts', { dot: true }), true);
  assert.equal(match('src/file.js', '**/*.{ts,js}'), true);
});

test('class and helper API used by glob and ESLint remains available', () => {
  assert.equal(new match.Minimatch('src/**/*.ts').match('src/app.ts'), true);
  assert.deepEqual(match.match(['a.ts', 'b.js'], '*.ts'), ['a.ts']);
  assert.deepEqual(require('glob').sync('**/*.cjs', { cwd: __dirname }).sort(), ['compat.test.cjs', 'index.cjs']);
  assert.deepEqual(match.braceExpand('a{1,2}.ts'), ['a1.ts', 'a2.ts']);
});

test('named API and legacy API use the same patched matcher', () => {
  const patched = require('minimatch-patched');
  assert.equal(match.defaults({ dot: true })('.hidden.ts', '*.ts'), true);
  assert.ok(new match.Minimatch('*.ts') instanceof patched.Minimatch);
  assert.equal(match.minimatch, patched.minimatch);
});
test('legacy Windows absolute path patterns discover lint targets', () => {
  const path = require('node:path');
  const matcher = new match.Minimatch(path.resolve('src/**/*.ts'), { dot: true, matchBase: true });
  assert.equal(matcher.match(path.resolve('src/app/app.component.ts')), true);
});