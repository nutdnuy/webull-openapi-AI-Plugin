---
name: webull-events
description: Explain and plan Webull Thailand real-time market-data MQTT subscriptions and gRPC trade-event subscriptions. Use for streaming architecture, topics, lifecycle, or event handling; do not pretend the shared HTTP CLI maintains persistent sessions.
---

# Webull events and streaming

Read `references/endpoints.json` and `references/authentication.md` for the documented request shapes and credentials. Consult the official [Webull Open API reference](https://developer.webull.co.th/apis/docs/webull-open-api-reference), [Market Data API FAQ](https://developer.webull.co.th/apis/docs/market-data-api/faq/), and [Trading API Getting Started](https://developer.webull.co.th/apis/docs/trade-api/getting-started/).

## Supported streaming interfaces

- `POST /openapi/market-data/streaming/subscribe` — MQTT market-data subscription operation; [official reference index](https://developer.webull.co.th/apis/docs/webull-open-api-reference).
- `POST /openapi/market-data/streaming/unsubscribe` — MQTT market-data unsubscribe operation; [official docs](https://developer.webull.co.th/apis/docs/reference/trade-api/unsubscribe/).
- `subscribeTradeEvents` — conceptual gRPC trade-event subscription (the catalog entry has `transport: grpc` and no HTTP method/path); [official getting-started docs](https://developer.webull.co.th/apis/docs/trade-api/getting-started/).

## Workflow

1. Read the catalog entry for the MQTT subscribe/unsubscribe request shape and the auth reference for connection prerequisites. Treat subscribe/unsubscribe as streaming lifecycle operations, not ordinary one-shot data reads.
2. Explain connection identity, topic/session lifecycle, heartbeat/reconnect behavior, permissions, and documented limits from the official docs. Do not promise delivery or silently restore subscriptions after disconnect unless the client explicitly implements that behavior.
3. The shared CLI is an HTTP request client. It does not open or hold persistent MQTT or gRPC sessions. You may use it only for a documented one-shot control request, with catalog-shaped placeholders:

   ```bash
   python scripts/webull_api.py request --method POST --path /openapi/market-data/streaming/subscribe --body-file ./subscribe.json --allow-write --write-confirmation STREAMING
   python scripts/webull_api.py request --method POST --path /openapi/market-data/streaming/unsubscribe --body-file ./unsubscribe.json --allow-write --write-confirmation STREAMING
   ```

4. Do not claim that the CLI received live binary protobuf/MQTT messages or gRPC order events. Recommend an official Webull SDK or a purpose-built persistent client for those sessions, with secrets kept outside logs and source control. Do not invent an HTTP path for `subscribeTradeEvents`.
