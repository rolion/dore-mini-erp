# Patched minimatch compatibility

Karma 6, karma-coverage and ESLint 9 dependencies still expect the old callable CommonJS minimatch export. Patched minimatch 11 exports that function as minimatch.minimatch.

This private adapter supplies the old entry point and re-exports patched helpers and extends the patched Minimatch class with legacy segment metadata. It contains no matching implementation or vulnerability suppression. npm tracks minimatch-patched as an alias of minimatch11.0.3, so the actual engine remains visible to npm audit.

The root override applies this adapter to all minimatch consumers. Glob13 is separately overridden to patched14.0.3; Glob7 is retained for Karma's callback API and uses the patched matcher through this adapter.

Run npm run test:tooling and the complete lint/build/Karma suite when changing it. Remove the adapter when the remaining legacy tooling supports the modern export shape natively.
Glob7 inspects parsed segments as RegExp-like objects. The adapter adds _glob and Symbol.match to the engine's existing Matcher objects; Symbol.match calls their existing nonrecursive test method. It does not generate regexes or replace the matching algorithm. The class also preserves legacy Windows backslash path handling for ESLint's absolute file patterns. Tests exercise wildcard traversal, matching/exclusion/defaults and Windows lint discovery.