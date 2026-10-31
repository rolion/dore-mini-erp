# Docker deployment Quality Gate — 2026-10-31

**Task:** TASK-docker-production-deployment
**Plan:** PLAN-2026-10-31-docker-production-deployment (v2), COMPLETO
**Verdict:** FAIL — existing frontend regression suite cannot compile; PR remains draft.
**Independent reviewer:** quality_gate subagent. Parent executed Docker commands after escalated agent command stalled; reviewer assessed literal parent evidence separately. No product fixes by reviewer.

## Results

| Criterion | Result / evidence |
|---|---|
| AC-01 | Both production images built with Docker; npm ci added1040 packages; Angular production bundle completed21.481s, initial2.22MB. Backend image ef20f53b9cc9; final frontend fd7420ee1462. |
| AC-02 | Compose config valid, only two services, exact requested domain/email variables, external proxy, no host ports. Runtime override used isolated proxy network without public domain registration. |
| AC-03 | Missing SECRET_KEY, DATABASE_URL, DATABASE_NETWORK each rejected. Backend image has no /app/.env. UID10001. External disposable PostgreSQL16 network used. |
| AC-04 | Nginx syntax, SPA deep paths, both domain health requests, API/admin forwarding, admin CSS, missing assets, HTTP redirect, admin login and cross-origin rejection all passed below. |
| AC-05 | compose up --wait reports both Healthy; startup collected154static files before frontend. Explicit migrations succeeded. README and runbook reviewed. |

## Commands and literal evidence

With synthetic runtime variables and isolated Compose project pocketbiz-quality-gate:

```text
docker compose -p pocketbiz-quality-gate build --progress plain
Image pocketbiz-backend:quality-gate Built
Image pocketbiz-frontend:quality-gate Built
```

After the reviewed missing-file routing fix, rebuilt frontend with cached npm ci:

```text
docker compose -p pocketbiz-quality-gate --progress plain build frontend
Application bundle generation complete. [21.481 seconds]
Image pocketbiz-frontend:quality-gate Built
```

```text
docker compose ... run --rm --no-deps backend python manage.py migrate --noinput
154 static files copied to '/app/staticfiles'.
Apply all migrations: accounts, admin, auth, authtoken, catalog, contenttypes, costing, customers, expenses, inventory, modularity, purchases, sales, sessions
All listed migrations: OK
```

Test settings intentionally bypass production collectstatic entrypoint:

```text
docker compose ... run --rm --no-deps --entrypoint python -e DJANGO_SETTINGS_MODULE=config.settings.test backend manage.py test config --noinput
Found 8 test(s).
System check identified no issues (0 silenced).
Ran 8 tests in 0.028s
OK
```

```text
.venv/Scripts/python.exe -m unittest config.test_production_deployment -v
Ran 5 tests in 0.025s
OK

npm.cmd run lint
All files pass linting.

.venv/Scripts/python.exe -m bandit config/settings/production.py -f txt
No issues identified.
```

```text
docker compose ... up -d --no-build --wait
Container pocketbiz-quality-gate-backend-1 Healthy
Container pocketbiz-quality-gate-frontend-1 Healthy

docker compose ... exec -T frontend nginx -t
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful

docker compose ... exec -T backend id
uid=10001(app) gid=10001(app) groups=10001(app)
No dotenv in image; admin CSS collected
```

Python http.client requests from backend to frontend port80, with actual Django admin user/session on disposable PostgreSQL and simulated original proxy Host/X-Forwarded-Proto:

```text
www.pocketbiz.website health=200 JSON
app.pocketbiz.website health=200 JSON
/pocketbiz/login SPA=200
/pocketbiz/sales/orders/123 SPA=200
admin CSS=200 text/css
/assets/does-not-exist.js =404
/missing.avif =404
/static/missing.css =404
/api/does-not-exist/ =404
HTTP redirect=301 correct HTTPS host/path
admin login with same-origin CSRF=302 /admin/
cross-origin admin POST=403
All container HTTP smoke checks passed
```

## Findings and scope

- REV-2026-10-31-docker-production-deployment-01: pre-existing Angular test compiler failure; no tests/coverage executed by Karma.
- REV-2026-10-31-docker-production-deployment-02: existing npm dependency advisories.
- No remaining deployment implementation defect identified. Review found uncommon root asset extensions could receive SPA fallback; implementation fixed and /missing.avif404 verified.
- Existing Sass deprecations and23 CSS selector warnings in production build.
- Broader Bandit config scan reports pre-existing Low B105 at config/tests.py:16 (synthetic test data). Changed production settings scan clean.
- Coverage/ruff/flake8/mypy not installed; no new installation. New settings branches manually mapped to five tests.
- DDD/tenancy/domain/schema unchanged; no visual changes, visual review inapplicable.
- Minor plan wording says restart frontend after backend recreation; actual dynamic Docker DNS makes restart a troubleshooting measure, as runbook explains.

## Limits

No real DNS, certificate issuance, public proxy configuration, browser visual review or droplet deployment performed. HTTP tests validate forwarding behind a simulated trusted TLS-terminating proxy. Do not interpret them as verification of live certificates.