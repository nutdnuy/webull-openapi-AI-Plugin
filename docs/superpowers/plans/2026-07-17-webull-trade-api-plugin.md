# Webull OpenAPI multi-skill hardening plan

## Goal

Maintain a public six-skill Claude/Codex plugin for the Webull Thailand OpenAPI with a signed, catalog-authorized runtime and safe packaging.

## Scope

- Keep `scripts/webull_api.py` as the single HTTP runtime.
- Load `references/endpoints.json` relative to the runtime source, with packaged-reference fallback for installed wheels.
- Allow only `api.webull.co.th` and `th-api.uat.webullbroker.com`.
- Read access tokens from `WEBULL_ACCESS_TOKEN`; read request bodies from files or stdin.
- Fail closed for unknown method/path pairs; use catalog `risk` and `confirmation` metadata for gates.
- Keep token check and batch bars as read operations; require `TOKEN_WRITE` only for token creation and `STREAMING` for streaming controls.
- Redact credential-bearing JSON keys by default and never expose app secrets or signature/authorization fields.
- Package version `0.2.0` as `webull-openapi` with the `webull-api` console script.

## Verification gates

Run `pytest -q`, `ruff check .`, `python -m compileall -q .`, all six skill `quick_validate.py` checks, and JSON parsing checks. Build a wheel, install it into a temporary Python 3.11+ virtual environment, and invoke `webull-api --help` plus an offline transport smoke where practical. Do not use live credentials or commit changes.
