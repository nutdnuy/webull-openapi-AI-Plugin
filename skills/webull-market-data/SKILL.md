---
name: webull-market-data
description: Retrieve read-only Webull Thailand market, instrument, analyst, and screener data for research and monitoring. Use for prices, quotes, bars, profiles, ratings, target prices, gainers-losers, or top-active lists; never treat the result as a trading instruction.
---

# Webull market data

Read the relevant endpoint objects in `references/endpoints.json` before every request and use `references/authentication.md` for headers/signatures. Consult the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference) for endpoint documentation and permissions.

## Supported read-only endpoints

All paths below are read-only data operations; use the official reference index linked above for the current method, parameters, response, and rate limit.

- `/openapi/market-data/stock/tick`
- `/openapi/market-data/stock/snapshot`
- `/openapi/market-data/stock/quotes`
- `/openapi/market-data/stock/footprint`
- `/openapi/market-data/stock/batch-bars`
- `/openapi/market-data/stock/bars`
- `/openapi/instrument/stock/list`
- `/openapi/instrument/company/profile`
- `/openapi/instrument/analyst/rating`
- `/openapi/instrument/analyst/target-price`
- `/openapi/market-data/screener/gainers-losers`
- `/openapi/market-data/screener/top-active`

## Request workflow

1. Identify the exact path and read its catalog entry. Construct query parameters, path parameters, and JSON body exactly as cataloged; do not guess symbol, market, timestamp, pagination, or batch shapes.
2. Invoke the shared client and preserve its structured response:

   ```bash
   python scripts/webull_api.py request --method GET --path /openapi/market-data/stock/snapshot --query-json '{"symbol":"<SYMBOL>","market":"<MARKET>"}'
   ```

   For a cataloged POST such as batch bars, use the catalog-shaped body:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/market-data/stock/batch-bars --body-file ./batch-bars.json
   ```

3. Require only the minimum identifiers and account context documented for that endpoint. Validate dates, symbols, intervals, and pagination before calling. For batches, keep the requested universe and time range explicit.
4. Label output as observed API data with its timestamp and environment. Report empty, partial, stale, permission, rate-limit, and error responses without filling gaps from memory.
5. Keep this skill read-only. Do not call watchlist or order endpoints, and do not infer buy/sell/hold instructions, price targets, or execution decisions from market data. Historical or analyst fields are research inputs, not forecasts or guarantees.
