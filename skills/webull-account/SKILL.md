---
name: webull-account
description: Read Webull Thailand account lists, asset balances, and positions for authorized monitoring and reconciliation. Use for account or portfolio-state reads only; this skill performs no account or order writes.
---

# Webull account reads

Read the matching `references/endpoints.json` entry, follow its `schema_ref` into `references/openapi.json`, and read `references/authentication.md` before constructing each request. Use the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference) as the source.

## First-use onboarding

Before the first account request, check the secure environment for `WEBULL_APP_KEY` and `WEBULL_APP_SECRET`. If the API Key is missing, ask the user to configure it through a secret manager or local environment and stop. Never request or echo secrets in chat.

## Supported endpoints

- `GET /openapi/account/list` — list authorized accounts; [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).
- `GET /openapi/assets/balance` — read balances; [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).
- `GET /openapi/assets/positions` — read positions; [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).

## Workflow

1. Start with `/openapi/account/list` when the account identifier is unknown. Do not guess or select an account silently.
2. For balance or positions, require an account id only if that endpoint’s catalog entry marks it required. Construct its location, query, and body fields from the catalog, not from this skill or another endpoint.
3. Invoke the runtime with placeholders only:

   ```bash
   python scripts/webull_api.py request --method GET --path /openapi/account/list
   python scripts/webull_api.py request --method GET --path /openapi/assets/balance --query-json '{"account_id":"<ACCOUNT_ID>"}'
   ```

   If the catalog specifies a different method or placement, follow the catalog.
4. Redact account ids when unnecessary, and never print tokens, signatures, or private identifiers beyond what the user needs. Treat balances and positions as sensitive personal financial data.
5. Report the environment, request timestamp, returned currency/units, and whether the response is complete. Do not calculate a recommendation, infer risk tolerance, or place/modify/cancel an order from these reads.
