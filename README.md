# Webull OpenAPI AI Plugin

[![CI](https://github.com/nutdnuy/webull-openapi-AI-Plugin/actions/workflows/ci.yml/badge.svg)](https://github.com/nutdnuy/webull-openapi-AI-Plugin/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/nutdnuy/webull-openapi-AI-Plugin)](LICENSE)
[![Webull OpenAPI](https://img.shields.io/badge/Webull-Thailand%20OpenAPI-1E88E5)](https://developer.webull.co.th/apis/docs/webull-open-api-reference)

Claude Code and Codex skills for the [Webull Thailand OpenAPI](https://developer.webull.co.th/apis/docs/webull-open-api-reference). Ask an AI coding agent to read market data, inspect accounts, manage watchlists, preview orders, and work with documented streaming events through one catalog-driven interface.

The plugin includes complete request, parameter, and response schemas for all 34 HTTP endpoints in [`references/openapi.json`](references/openapi.json), plus catalog entries for MQTT and gRPC transports. Writes are explicitly gated and output is redacted by default.

## Features & Usage

Install the plugin in Claude Code or Codex, then ask in plain language—for example, “get an AAPL snapshot” or “preview this order without placing it.” The relevant skill reads the endpoint catalog and schema before using the shared runtime.

**Market Data** — Get ticks, snapshots, quotes, footprint data, historical bars, instruments, analyst data, and screeners.

**Account & Portfolio Reads** — List accounts, balances, positions, open orders, and order details as read-only operations.

**Watchlists** — Read watchlists and instruments, with explicit confirmation before create, update, or delete operations.

**Order Workflow** — Preview, read, place, replace, and cancel orders with separate confirmation gates for each write action.

**Authentication** — Create and check tokens, generate signed requests, and follow the documented 2FA lifecycle.

**Streaming Events** — Use the documentation and catalog for MQTT market-data and gRPC trade-event subscriptions.

**Schema-first Requests** — Every HTTP endpoint maps to a checked-in schema reference, so agents can inspect required parameters and response shapes before calling it.

## Requirements

- A Claude Code or Codex installation that supports local/GitHub plugins and skills.
- Python 3.11+ for the bundled `webull-api` runtime.
- Authorized Webull Thailand OpenAPI access.
- UAT credentials for initial testing; use production only after verifying the environment and host.

## Installation

### Claude Code

Install this repository using your Claude Code plugin workflow, or clone it locally and load the plugin directory. The Claude manifest is [`.claude-plugin/plugin.json`](.claude-plugin/plugin.json).

### Codex

Install this repository using your Codex plugin workflow, or clone it locally and load the plugin directory. The Codex manifest is [`.codex-plugin/plugin.json`](.codex-plugin/plugin.json).

### From source

```bash
git clone https://github.com/nutdnuy/webull-openapi-AI-Plugin.git
cd webull-openapi-AI-Plugin
python -m pip install .
```

This installs the `webull-api` command. For development and tests:

```bash
python -m pip install -e '.[test]'
pytest -q
```

## First use: configure your API Key

On the first request, the selected skill checks whether the Webull credentials are configured. If the API Key is missing, it asks you to set it up securely and stops before making a network request.

Configure credentials in your shell, a local secret manager, or an ignored environment file:

```bash
export WEBULL_APP_KEY='your-app-key'
export WEBULL_APP_SECRET='your-app-secret'
export WEBULL_ENV='uat'
```

Never paste the App Secret, access token, or private credentials into chat, source files, shell history, or Git. `WEBULL_ACCESS_TOKEN` may be set in the environment when a token is already available. See [`references/authentication.md`](references/authentication.md) for the complete authentication flow.

## Quick start

Ask Claude Code or Codex:

```text
Get a read-only market snapshot for AAPL in UAT and summarize the response.
```

Or use the runtime directly with schema-derived example payloads:

```bash
webull-api request \
  --method GET \
  --path /openapi/market-data/stock/snapshot \
  --query-json "$(cat examples/stock-snapshot.query.json)"

webull-api request \
  --method POST \
  --path /openapi/market-data/stock/batch-bars \
  --body-file examples/historical-bars.body.json
```

The examples contain placeholders, not credentials or complete production payloads. Use `--body-stdin` when a request body must not appear in shell history. The runtime redacts sensitive fields by default.

## Skills

| Skill | Scope |
| --- | --- |
| `webull-auth` | Token creation/check, signatures, environment, and 2FA lifecycle |
| `webull-market-data` | Market data, instruments, analysts, and screeners |
| `webull-account` | Accounts, balances, positions, and order reads |
| `webull-watchlists` | Watchlist and instrument reads plus confirmed writes |
| `webull-orders` | Preview, order reads, and gated place/replace/cancel |
| `webull-events` | MQTT market data and gRPC trade-event guidance |

See the complete endpoint inventory in [`references/endpoints.json`](references/endpoints.json). The generated OpenAPI-style reference is in [`references/openapi.json`](references/openapi.json).

## Safety & privacy

- Read operations do not authorize trades and are not investment advice.
- Token creation requires `TOKEN_WRITE`; order preview requires `PREVIEW`.
- Place, replace, and cancel require exact `PLACE`, `REPLACE`, or `CANCEL` confirmation immediately before the write.
- Watchlist and instrument writes require explicit confirmation; streaming controls require `STREAMING`.
- The runtime uses an allowlisted Webull host and fails closed for unknown method/path combinations.
- Request output is redacted by default. App secrets, access tokens, signatures, and authorization fields are never displayed by default.
- API acceptance does not guarantee order execution or fill. Verify every sensitive action and confirm the environment before writing.

Network requests are made only when the user invokes a skill or the runtime directly. Credentials remain in the local environment; they are not stored in this repository.

## Development

```bash
# Run tests
pytest -q

# Validate all six skills
python /path/to/skill-creator/scripts/quick_validate.py skills/webull-auth

# Inspect the generated endpoint schemas
python scripts/build_openapi_reference.py
```

The CI workflow runs the plugin contract tests, runtime tests, Ruff, and skill validation. The source layout is intentionally small:

```text
skills/                 # Claude Code and Codex skill instructions
scripts/webull_api.py   # signed, catalog-driven HTTP runtime
references/endpoints.json
references/openapi.json # complete HTTP request/response schemas
references/authentication.md
examples/               # placeholder request payloads
tests/                  # contract and runtime tests
```

## Official documentation

- [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference)
- [Market Data API FAQ](https://developer.webull.co.th/apis/docs/market-data-api/faq/)
- [Trading API Getting Started](https://developer.webull.co.th/apis/docs/trade-api/getting-started/)
- [Server-to-server authentication](https://developer.webull.co.th/apis/docs/reference/trade-api/server-to-server/)

## License

Licensed under the [MIT License](LICENSE).

This project is an interface client and research tool—not a financial advice service, recommendation engine, or guarantee of order execution. Use it only with authorized Webull access.
