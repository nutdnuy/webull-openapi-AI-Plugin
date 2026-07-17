"""Signed, fail-closed Webull Open API client and command-line entry point."""

from __future__ import annotations

import argparse
import base64
import hashlib
import hmac
import json
import os
import secrets
import sys
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import quote

import httpx


DEFAULT_API_HOST = "api.webull.co.th"
UAT_API_HOST = "th-api.uat.webullbroker.com"
DEFAULT_TIMEOUT_SECONDS = 30.0
SIGNATURE_ALGORITHM = "HMAC-SHA256"
SIGNATURE_VERSION = "1.0"
API_VERSION = "v2"
CONFIRMATIONS = frozenset(
    {
        "PREVIEW",
        "PLACE",
        "REPLACE",
        "CANCEL",
        "WATCHLIST_WRITE",
        "TOKEN_WRITE",
        "STREAMING",
    }
)
ALLOWED_HOSTS = frozenset({DEFAULT_API_HOST, UAT_API_HOST})
ALWAYS_REDACT_TERMS = ("secret", "signature", "authorization", "credential")


class WebullAPIError(RuntimeError):
    """A safe, non-secret-bearing Webull client error."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        self.status_code = status_code
        super().__init__(message)


class WebullTimeoutError(WebullAPIError):
    """The request exceeded the configured timeout."""


class WriteConfirmationError(WebullAPIError):
    """A mutating request was not explicitly confirmed."""


class EndpointNotAllowedError(WebullAPIError):
    """The method/path pair is not present in the checked-in endpoint catalog."""


def utc_timestamp() -> str:
    """Return the UTC ISO-8601 timestamp required by the API."""

    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def generate_signature(
    *,
    path: str,
    query_params: Mapping[str, Any] | None,
    body: bytes,
    app_key: str,
    app_secret: str,
    host: str,
    timestamp: str,
    nonce: str,
) -> str:
    """Generate the official URL-encoded HMAC-SHA256 signature."""

    signing_headers = {
        "host": host,
        "x-app-key": app_key,
        "x-signature-algorithm": SIGNATURE_ALGORITHM,
        "x-signature-nonce": nonce,
        "x-signature-version": SIGNATURE_VERSION,
        "x-timestamp": timestamp,
    }
    merged: dict[str, str] = {
        str(key): str(value) for key, value in (query_params or {}).items()
    }
    merged.update(signing_headers)
    str1 = "&".join(f"{key}={merged[key]}" for key in sorted(merged))
    str3 = f"{path}&{str1}"
    if body:
        body_hash = hashlib.sha256(body).hexdigest().upper()
        str3 = f"{str3}&{body_hash}"
    encoded = quote(str3, safe="")
    digest = hmac.new(
        (app_secret + "&").encode("utf-8"), encoded.encode("utf-8"), hashlib.sha256
    ).digest()
    return base64.b64encode(digest).decode("ascii")


@lru_cache(maxsize=1)
def endpoint_catalog() -> dict[tuple[str, str], dict[str, Any]]:
    """Load the checked-in catalog beside this source file."""

    catalog_path = Path(__file__).resolve().parents[1] / "references" / "endpoints.json"
    if not catalog_path.is_file():
        # The wheel packages the references namespace; this keeps the installed
        # console script usable when its source tree is no longer present.
        from importlib.resources import files

        catalog_path = files("references").joinpath("endpoints.json")
    parsed = json.loads(catalog_path.read_text(encoding="utf-8"))
    entries = parsed.get("entries")
    if not isinstance(entries, list):
        raise ValueError("endpoint catalog must contain an entries list")
    return {
        (str(entry["method"]).upper(), str(entry["path"]).rstrip("/").lower()): entry
        for entry in entries
        if entry.get("method") and entry.get("path")
    }


def catalog_entry(method: str, path: str) -> dict[str, Any]:
    """Return a catalog entry or fail closed before any network call."""

    key = (method.upper(), path.rstrip("/").lower())
    try:
        return endpoint_catalog()[key]
    except KeyError as exc:
        raise EndpointNotAllowedError(
            f"endpoint is not authorized by references/endpoints.json: {method.upper()} {path}"
        ) from exc


def expected_confirmation(method: str, path: str) -> str | None:
    """Return the catalog-declared confirmation category, if one is required."""

    return catalog_entry(method, path).get("confirmation")


def validate_host(host: str) -> str:
    if host not in ALLOWED_HOSTS:
        raise ValueError(
            "host must be exactly api.webull.co.th or th-api.uat.webullbroker.com"
        )
    return host


def redact_secrets(value: Any, *, include_tokens: bool = True) -> Any:
    """Recursively redact values whose keys identify credential material."""

    if isinstance(value, Mapping):
        terms = ALWAYS_REDACT_TERMS + (("token", "app_key") if include_tokens else ())
        return {
            key: "[REDACTED]"
            if any(term in str(key).lower() for term in terms)
            else redact_secrets(item, include_tokens=include_tokens)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_secrets(item, include_tokens=include_tokens) for item in value]
    if isinstance(value, tuple):
        return [redact_secrets(item, include_tokens=include_tokens) for item in value]
    return value


class WebullClient:
    """Reusable signed Webull client. No retry is performed, especially for writes."""

    def __init__(
        self,
        app_key: str,
        app_secret: str,
        *,
        host: str = DEFAULT_API_HOST,
        timeout: float = DEFAULT_TIMEOUT_SECONDS,
        http_client: httpx.Client | None = None,
        transport: httpx.BaseTransport | None = None,
        timestamp_factory: Callable[[], str] = utc_timestamp,
        nonce_factory: Callable[[], str] | None = None,
    ) -> None:
        if not app_key or not app_secret:
            raise ValueError("WEBULL_APP_KEY and WEBULL_APP_SECRET are required")
        validate_host(host)
        self.app_key = app_key
        self.app_secret = app_secret
        self.access_token = os.getenv("WEBULL_ACCESS_TOKEN")
        self.host = host
        self.timeout = timeout
        self._timestamp_factory = timestamp_factory
        self._nonce_factory = nonce_factory or (lambda: secrets.token_hex(16))
        self._owns_client = http_client is None
        self._http_client = http_client or httpx.Client(
            base_url=f"https://{host}", timeout=timeout, transport=transport
        )

    @classmethod
    def from_env(cls, **kwargs: Any) -> "WebullClient":
        """Build a client from the supported environment variables only."""

        environment_value = os.getenv("WEBULL_ENV")
        environment = (environment_value or "prod").lower()
        if environment not in {"uat", "prod"}:
            raise ValueError("WEBULL_ENV must be uat or prod")
        expected_host = UAT_API_HOST if environment == "uat" else DEFAULT_API_HOST
        host = os.getenv("WEBULL_API_HOST", expected_host)
        validate_host(host)
        if environment_value is not None and "WEBULL_API_HOST" in os.environ and host != expected_host:
            raise ValueError("WEBULL_ENV and WEBULL_API_HOST select different hosts")
        timeout = float(os.getenv("WEBULL_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS))
        return cls(
            os.getenv("WEBULL_APP_KEY", ""),
            os.getenv("WEBULL_APP_SECRET", ""),
            host=host,
            timeout=timeout,
            **kwargs,
        )

    def close(self) -> None:
        if self._owns_client:
            self._http_client.close()

    def __enter__(self) -> "WebullClient":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def request(
        self,
        method: str,
        path: str,
        *,
        query: Mapping[str, Any] | None = None,
        body: bytes | str | None = None,
        allow_write: bool = False,
        write_confirmation: str | None = None,
    ) -> Any:
        method = method.upper()
        if not path.startswith("/"):
            raise ValueError("path must start with /")
        entry = catalog_entry(method, path)
        risk = entry.get("risk")
        if risk not in {"read", "write", "streaming"}:
            raise EndpointNotAllowedError("endpoint catalog has an unsupported risk")
        expected = expected_confirmation(method, path)
        if risk in {"write", "streaming"}:
            if not allow_write:
                raise WriteConfirmationError(
                    "this endpoint requires --allow-write and exact confirmation"
                )
            if not write_confirmation or write_confirmation != expected:
                raise WriteConfirmationError(
                    f"confirmation must be exactly {expected} for this catalog entry"
                )

        body_bytes = body.encode("utf-8") if isinstance(body, str) else (body or b"")
        timestamp = self._timestamp_factory()
        nonce = self._nonce_factory()
        headers = {
            "x-app-key": self.app_key,
            "x-timestamp": timestamp,
            "x-signature-algorithm": SIGNATURE_ALGORITHM,
            "x-signature-version": SIGNATURE_VERSION,
            "x-signature-nonce": nonce,
            "x-version": API_VERSION,
            "host": self.host,
        }
        if self.access_token:
            headers["x-access-token"] = self.access_token
        headers["x-signature"] = generate_signature(
            path=path,
            query_params=query,
            body=body_bytes,
            app_key=self.app_key,
            app_secret=self.app_secret,
            host=self.host,
            timestamp=timestamp,
            nonce=nonce,
        )
        if body_bytes:
            headers["content-type"] = "application/json"
        try:
            response = self._http_client.request(
                method,
                path,
                params=dict(query or {}),
                content=body_bytes or None,
                headers=headers,
                timeout=self.timeout,
            )
        except httpx.TimeoutException as exc:
            raise WebullTimeoutError("Webull request timed out") from exc
        except httpx.HTTPError as exc:
            raise WebullAPIError("Webull request failed before receiving a response") from exc
        if response.status_code >= 400:
            raise WebullAPIError(
                f"Webull request failed with status {response.status_code}",
                status_code=response.status_code,
            )
        if not response.content:
            return None
        try:
            return response.json()
        except ValueError as exc:
            raise WebullAPIError("Webull returned a non-JSON response") from exc


def _json_object(value: str, flag: str) -> Mapping[str, Any]:
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{flag} must be valid JSON") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{flag} must be a JSON object")
    return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    request = subparsers.add_parser("request", help="make one signed API request")
    request.add_argument("--method", required=True)
    request.add_argument("--path", required=True)
    request.add_argument("--query-json", default="{}")
    body_source = request.add_mutually_exclusive_group()
    body_source.add_argument("--body-file", type=Path)
    body_source.add_argument("--body-stdin", action="store_true")
    request.add_argument("--host", choices=sorted(ALLOWED_HOSTS))
    request.add_argument("--allow-write", action="store_true")
    request.add_argument("--write-confirmation")
    output = request.add_mutually_exclusive_group()
    output.add_argument("--redact-secrets", dest="redact", action="store_true", default=True)
    output.add_argument("--show-secrets", dest="redact", action="store_false")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        query = _json_object(args.query_json, "--query-json")
        body = None
        if args.body_file is not None:
            body = args.body_file.read_bytes()
        elif args.body_stdin:
            body = sys.stdin.buffer.read()
        overrides: dict[str, Any] = {}
        if args.host:
            overrides["host"] = args.host
        with WebullClient.from_env(**overrides) as client:
            result = client.request(
                args.method,
                args.path,
                query=query,
                body=body,
                allow_write=args.allow_write,
                write_confirmation=args.write_confirmation,
            )
        json.dump(
            redact_secrets(result, include_tokens=args.redact) if args.redact else redact_secrets(result, include_tokens=False),
            sys.stdout,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        sys.stdout.write("\n")
        return 0
    except (ValueError, WebullAPIError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
