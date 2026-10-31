# REV-2026-10-31-docker-production-deployment-02: Existing npm dependency advisories

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-31-docker-production-deployment.md (v2)
**Spec reference:** Security review
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
Existing frontend dependencies contain advisories. package.json is unchanged; existing local lockfile was committed unchanged for reproducible production builds. No automatic audit fix or dependency downgrade was applied.

## Expected behavior
Advisories are assessed/remediated in a dependency maintenance task before production approval.

## Actual behavior / Evidence
```text
npm.cmd audit --omit=dev --json --fetch-retries=0 --fetch-timeout=15000
metadata.vulnerabilities:
info:0 low:0 moderate:4 high:2 critical:0 total:6
exit code 1
```

High: lodash-es (template code injection/prototype pollution), xlsx (prototype pollution/ReDoS).
Moderate: browser-sync, echarts, minimatch, resp-modifier.
The full Docker builder npm ci audit includes development packages:
```text
108 vulnerabilities (3 low, 98 moderate, 7 high)
```

nginx runtime ships compiled assets, not node_modules or npm development tools. This does not dismiss advisories in bundled browser dependencies. Treat audit counts as dependency metadata, not proof of exploitability.

Advisory references returned by audit:
- https://github.com/advisories/GHSA-r5fr-rjxr-66jc
- https://github.com/advisories/GHSA-4r6h-8v6p-xvw6
- https://github.com/advisories/GHSA-5pgg-2g8v-p4x9
- https://github.com/advisories/GHSA-fgmj-fm8m-jvvx
## Resolution (2026-10-31)
Explicit user-authorized remediation reviewed independently at commit63bd4a7: PASS. See QA-2026-10-31-docker-production-deployment-remediation.md. Full frontend suite1060SUCCESS; full and production npm audit zero vulnerabilities; locked production build and runtime smoke pass. Original evidence above retained as history.
