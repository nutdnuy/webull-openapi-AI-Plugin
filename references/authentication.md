# Webull API authentication

Official references: [API index](https://developer.webull.co.th/apis/docs/webull-open-api-reference), [signature](https://developer.webull.co.th/apis/docs/authentication/signature), and [token lifecycle](https://developer.webull.co.th/apis/docs/authentication/token). The algorithm is also implemented by the [current official Python SDK](https://github.com/webull-inc/webull-openapi-python-sdk).

## Base URLs and environment

Production uses `https://api.webull.co.th`. The documented UAT API host is `https://th-api.uat.webullbroker.com`; select it with `WEBULL_ENV=uat` or the exact `WEBULL_API_HOST` value. Only these two hosts are accepted, and conflicting environment selections fail before network access.

Required environment variables are `WEBULL_APP_KEY` and `WEBULL_APP_SECRET`. Optional variables are `WEBULL_ACCESS_TOKEN`, `WEBULL_API_HOST`, and `WEBULL_TIMEOUT_SECONDS`. `WEBULL_API_KEY` and Bearer authentication are deliberately unsupported.

## Signature summary

Each request sends `x-app-key`, UTC ISO-8601 `x-timestamp`, `x-signature-algorithm: HMAC-SHA256`, `x-signature-version: 1.0`, a fresh `x-signature-nonce`, and `x-version: v2`; it also sends `x-access-token` when configured. The signing set merges query parameters with `host` and the signing headers, sorts names, joins `name=value` pairs, appends the uppercase SHA-256 body hash when a body exists, URL-encodes the complete string, and computes Base64 HMAC-SHA256 with `app_secret + "&"`. `x-signature` and `x-version` are excluded from the signed set. The current official signature page and SDK use SHA-256 for the body digest; the historical worked example’s displayed body digest/signature is internally inconsistent, so this runtime follows the documented algorithm rather than reproducing that inconsistent value.

## Token 2FA lifecycle

Create a token; it starts as `PENDING` and requires SMS verification in the Webull app. Verification changes it to `NORMAL`. A pending token expires after five minutes, and a token can become `INVALID` after 15 consecutive days without API calls. UAT tokens are valid by default. Check status before reuse when needed, then store active tokens securely and send them as `x-access-token`.

## Security rules

The app secret is used only locally to compute signatures and is never sent as a header. The runtime reads access tokens only from `WEBULL_ACCESS_TOKEN`; it accepts request bodies only from `--body-file` or `--body-stdin`, never from argv JSON. JSON output is recursively redacted by default for token, secret, signature, authorization, credential, and app_key fields; `--show-secrets` is explicit but still always redacts secret/signature/authorization/credential fields. The runtime uses the catalog to reject unknown endpoints before network access, requires `--allow-write` plus the catalog’s exact confirmation for writes, and requires `STREAMING` for streaming controls. It never logs credentials, signed headers, request bodies, or response bodies on errors, never retries writes, and tests use offline transports only.
