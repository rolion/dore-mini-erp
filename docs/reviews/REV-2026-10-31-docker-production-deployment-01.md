# REV-2026-10-31-docker-production-deployment-01: Existing frontend suite cannot compile

**Status:** Resolved
**Severity:** High
**Category:** IMPLEMENTATION
**Related plan:** docs/plans/PLAN-2026-10-31-docker-production-deployment.md (v2)
**Spec reference:** Regression tests / delivery-publish gate
**Plan mode:** COMPLETO
**Suggested owner:** delivery-build

## Description
An unchanged generated root component test expects a title field removed from the application. This is baseline debt, not introduced by deployment. The strict delivery-publish rule does not permit PASS with a failed suite unless explicitly accepted by the user. No acceptance has been requested or granted.

## Expected behavior
Frontend regression suite compiles and runs.

## Actual behavior
Karma compilation fails before tests or coverage run.

## Evidence
```text
npm.cmd test -- --watch=false --browsers=ChromeHeadless --code-coverage
TS2339: Property 'title' does not exist on type 'AppComponent'.
src/app/app.component.spec.ts:24:
expect(app.title).toEqual('oreva');
exit code 1
```

Independent reviewer confirmed git diff origin/main for app.component.spec.ts and app.component.ts is empty, and origin/main contains the same stale expectation. Remediation would change unrelated frontend tests and is not included silently in this infrastructure task.
## Resolution (2026-10-31)
Explicit user-authorized remediation reviewed independently at commit63bd4a7: PASS. See QA-2026-10-31-docker-production-deployment-remediation.md. Full frontend suite1060SUCCESS; full and production npm audit zero vulnerabilities; locked production build and runtime smoke pass. Original evidence above retained as history.
