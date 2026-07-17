---
name: webull-watchlists
description: Read and manage Webull Thailand watchlists and their instruments. Use for watchlist inspection or explicitly requested changes; GET list is read-only and every create, update, add, or remove operation requires explicit confirmation.
---

# Webull watchlists

Read the relevant object in `references/endpoints.json`, follow its `schema_ref` into `references/openapi.json`, and read `references/authentication.md` before building parameters or JSON. Consult the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference).

## Supported endpoints

- `GET /openapi/market-data/watchlist/list` — read-only list.
- `POST /openapi/market-data/watchlist/create`
- `POST /openapi/market-data/watchlist/update`
- `POST /openapi/market-data/watchlist/delete`
- `GET /openapi/market-data/watchlist/instruments/list` — read-only instrument list.
- `POST /openapi/market-data/watchlist/instruments/add`
- `POST /openapi/market-data/watchlist/instruments/update`
- `POST /openapi/market-data/watchlist/instruments/remove`

All paths are documented in the [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).

## Workflow and confirmation gate

1. Use the catalog entry to determine the exact method, identifiers, parameter placement, and body schema. Do not reuse a body between watchlist endpoints or invent a watchlist id.
2. Execute read-only list calls directly when authorized:

   ```bash
   python scripts/webull_api.py request --method GET --path /openapi/market-data/watchlist/list
   python scripts/webull_api.py request --method GET --path /openapi/market-data/watchlist/instruments/list --query-json '{"watchlist_id":"<WATCHLIST_ID>"}'
   ```

3. For every write path, first summarize the exact endpoint, target watchlist/instrument, and redacted request body. Ask for explicit confirmation immediately before the call. A request to “show”, “review”, or “find” a watchlist never authorizes a write.
4. After confirmation, invoke the catalog-shaped request, for example:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/market-data/watchlist/create --body-file ./watchlist-create.json --allow-write --write-confirmation WATCHLIST_WRITE
   ```

5. Report the response and any returned identifiers. Never expose secrets, and never turn a watchlist change into an order or investment recommendation.
