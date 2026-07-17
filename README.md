# Webull OpenAPI skills

Public Claude Code and Codex plugin packaging for the Webull Thailand OpenAPI. The six skills cover authentication, read-only market and account data, guarded watchlist and order operations, and documentation for MQTT/gRPC events. A shared runtime is expected at `scripts/webull_api.py`; the endpoint catalog and authentication reference are expected at `references/endpoints.json` and `references/authentication.md`.

## Skill map

| Skill | Scope |
| --- | --- |
| `webull-auth` | Token creation/check, signatures, environment, 2FA lifecycle |
| `webull-market-data` | Tick, snapshot, quotes, footprint, bars, instruments, analysts, screeners |
| `webull-account` | Accounts, balances, positions (read-only) |
| `webull-watchlists` | Watchlist and instrument reads plus confirmed writes |
| `webull-orders` | Preview, order reads, and gated place/replace/cancel |
| `webull-events` | MQTT market data and gRPC trade-event subscription guidance |

## Install and use

Install this repository as a Claude Code or Codex plugin using the platform’s local/GitHub plugin workflow. For the Python CLI, install the wheel with `python -m pip install .`; this provides the `webull-api` console command. Configure secrets through a local secret manager or ignored environment file; never commit credentials. Use UAT first and select production only deliberately.

Every request must read the relevant catalog entry first:

```bash
python scripts/webull_api.py request --method GET --path /openapi/market-data/stock/snapshot --query-json '{"symbol":"<SYMBOL>","market":"<MARKET>"}'
python scripts/webull_api.py request --method GET --path /openapi/account/list
python scripts/webull_api.py request --method POST --path /openapi/trade/order/preview --body-file ./request.json
```

The exact flags and schema are defined by the shared runtime/catalog contract; placeholders above are not credentials or complete production payloads. Use `--body-stdin` when the JSON must never appear in shell history, and set `WEBULL_ACCESS_TOKEN` in the environment rather than passing a token argument. Output is redacted by default; use `--show-secrets` only for an explicitly authorized diagnostic, noting that app secrets and signature/authorization fields remain redacted.

## Configuration and environments

Use `WEBULL_APP_KEY`, `WEBULL_APP_SECRET`, the token variable documented by `references/authentication.md` (for example `WEBULL_ACCESS_TOKEN` if that reference specifies it), and the runtime’s explicit host/environment variable. Keep them in environment variables or a secret manager, redact them in logs, and do not paste them into chat. UAT and production hosts are distinct: verify the host in the official documentation and make the environment visible in every write summary. Do not use production credentials against UAT or vice versa.

## Safety gates

- Market-data, account, history, open-order, and order-detail reads are read-only; they are not trading advice or authorization to trade.
- Token creation is write-like and requires `TOKEN_WRITE` confirmation; token check is a cataloged read and needs no write gate.
- Watchlist create/update/delete and instrument add/update/remove require explicit confirmation immediately before the write.
- Order preview requires `PREVIEW`; place, replace, and cancel require exact confirmation with `PLACE`, `REPLACE`, or `CANCEL` respectively. Streaming controls require `STREAMING`.
- Show the redacted payload summary before writes. Never infer a trade from a research request. API acceptance does not guarantee execution or fill.

## Official documentation

- [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference)
- [Market Data API FAQ](https://developer.webull.co.th/apis/docs/market-data-api/faq/)
- [Trading API Getting Started](https://developer.webull.co.th/apis/docs/trade-api/getting-started/)
- [Server-to-server authentication](https://developer.webull.co.th/apis/docs/reference/trade-api/server-to-server/)

## Tests and license

Run the repository’s test suite with `pytest -q`. Validate the six skills with the skill-creator `quick_validate.py` script and parse all JSON manifests before publishing. This repository’s plugin metadata is MIT-licensed; review any bundled runtime or reference files for their own license terms.

This is an interface client and research tool—not financial advice, a recommendation engine, or a guarantee of order execution. Use it only with authorized Webull access and independently verify every sensitive action.
