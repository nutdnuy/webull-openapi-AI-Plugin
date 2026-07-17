---
name: webull-auth
description: Create, check, and safely troubleshoot Webull Thailand OpenAPI access tokens, signatures, environment setup, and the 2FA verification lifecycle. Use when a request concerns authentication or token status, never when it is merely a market-data or trading query.
---

# Webull authentication

Read `references/authentication.md`, the matching `references/endpoints.json` entry, and its `schema_ref` in `references/openapi.json` before constructing any request. Use the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference) for current details.

## Supported endpoints

- `POST /openapi/auth/token/create` — [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference). Treat token creation as a sensitive write-like operation: require explicit `TOKEN_WRITE` confirmation immediately before calling it.
- `POST /openapi/auth/token/check` — [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference). The catalog marks this as a credential-status read; still handle token material as secret.

## Workflow

1. Load only the required environment variables from a local secret manager or shell environment. Never ask the user to paste a secret into chat, never print secrets, and redact tokens, signatures, authorization headers, and response fields containing credential material.
2. Read the catalog entry to determine the HTTP method, required headers, query parameters, and JSON body. Do not invent fields or copy a neighboring endpoint’s schema.
3. For token creation, summarize the intended operation and wait for exact `TOKEN_WRITE` confirmation; then invoke the shared runtime, for example:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/auth/token/create --body-file ./token-create.json
   ```

4. For status checks, invoke the catalog-shaped request only after confirming the token is available through the configured secret source. No write gate is required because this endpoint is cataloged as `risk: read`:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/auth/token/check --body-file ./token-check.json
   ```

5. Explain the documented lifecycle: creation normally returns `PENDING`; the user completes mobile-app SMS/2FA verification, then check status until `NORMAL`. `INVALID` or `EXPIRED` requires a new token. Never claim that a token is active without the check response.
6. Use UAT first. Keep production host selection explicit and separate from credential setup. Do not persist tokens in source control, logs, examples, or generated reports.

## Safe handling

Do not expose a complete request or response when it contains a token or signed header; show a redacted summary instead. Do not bypass signature prerequisites, substitute bearer-token guesses, or infer missing app credentials. Authentication success does not authorize an order or any other write.
