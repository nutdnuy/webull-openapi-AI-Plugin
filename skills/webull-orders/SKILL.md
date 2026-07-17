---
name: webull-orders
description: Preview, inspect, place, replace, and cancel Webull Thailand stock orders with explicit safety gates. Use for a concrete user-authorized order workflow, never infer an order from research, market-data, or portfolio questions.
---

# Webull orders

Read the exact endpoint entries in `references/endpoints.json` and authentication rules in `references/authentication.md` before building any request. Use the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference) and current trading documentation.

## Supported endpoints

- `POST /openapi/trade/order/preview` — preview only; gate with `PREVIEW`.
- `POST /openapi/trade/order/place` — write; require exact confirmation and `PLACE`.
- `POST /openapi/trade/order/replace` — write; require exact confirmation and `REPLACE`.
- `POST /openapi/trade/order/cancel` — write; require exact confirmation and `CANCEL`.
- `GET /openapi/trade/order/history` — read-only history.
- `GET /openapi/trade/order/open` — read-only open orders.
- `GET /openapi/trade/order/detail` — read-only detail.

All paths are documented in the [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).

## Safety workflow

1. For preview, obtain the exact user-provided instrument, side, quantity, order type, price/trigger, time-in-force, account, and other catalog-required fields. Read the catalog before constructing the body, then ask for `PREVIEW` confirmation:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/trade/order/preview --body-file ./order-preview.json --allow-write --write-confirmation PREVIEW
   ```

2. Before place, replace, or cancel, display a concise request-payload summary: environment, account (redacted), symbol, side, quantity, order type, price/trigger, time-in-force, client order id, and the exact operation. Do not execute until the user gives the corresponding exact gate: `PLACE`, `REPLACE`, or `CANCEL`.
3. Construct each body independently from `references/endpoints.json`; never copy preview output blindly into a write request and never infer missing fields. Invoke only after confirmation, using the documented method/path:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/trade/order/place --body-file ./order-place.json --allow-write --write-confirmation PLACE
   ```

4. Treat history/open/detail as reads and redact private identifiers. Never infer a trade instruction from “analyze”, “research”, “compare”, “watch”, or “what should I buy?”
5. Surface rate-limit responses and avoid automatic retries for writes. State clearly that an accepted API request is not a guarantee of execution, fill, price, or market availability. Do not claim success until the API response confirms it.
