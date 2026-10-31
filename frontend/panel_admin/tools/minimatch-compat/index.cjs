// Legacy Glob/Karma consumers expect a callable export and RegExp-like parsed
// segments. Delegate to minimatch's patched nonrecursive engine throughout.
const patched = require('minimatch-patched');

function compatibleApi(api) {
  const match = typeof api === 'function' ? api : api.minimatch;
  const callable = (path, pattern, options) => match(path, pattern, options);
  Object.assign(callable, api);
  callable.Minimatch = class extends api.Minimatch {
    constructor(pattern, options) {
      super(pattern, {
        ...options,
        windowsPathsNoEscape: options?.windowsPathsNoEscape ?? process.platform === 'win32',
      });
      for (const row of this.set) {
        for (const segment of row) {
          if (segment && typeof segment === 'object' && typeof segment.test === 'function') {
            segment._glob = segment.pattern;
            segment[Symbol.match] = (value) => segment.test(value) ? [value] : null;
          }
        }
      }
    }
  };
  callable.defaults = (options) => compatibleApi(api.defaults(options));
  return callable;
}

module.exports = compatibleApi(patched);