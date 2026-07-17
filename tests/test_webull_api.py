from __future__ import annotations

import hashlib
import io
import httpx
import pytest

from scripts.webull_api import (
    WebullAPIError,
    WebullClient,
    EndpointNotAllowedError,
    WriteConfirmationError,
    build_parser,
    generate_signature,
    main,
)


def test_official_signature_example_uses_documented_inputs() -> None:
    # The published page labels its 32-character body digest SHA256, but the
    # displayed digest is the MD5 of the compact JSON body. Keep the fixture
    # explicit so the published worked-example signature remains regression-tested.
    body = b'{"k1":123,"k2":"this is the api request body","k3":true,"k4":{"foo":[1,2]}}'
    documented_sha256 = hashlib.sha256(body).hexdigest().upper()
    published_worked_example_digest = hashlib.md5(body).hexdigest().upper()
    path = "/trade/place_order"
    query = {"a1": "webull", "a2": "123", "a3": "xxx", "q1": "yyy"}
    headers = {
        "host": "api.webull.com.sg",
        "x-app-key": "776da210ab4a452795d74e726ebd74b6",
        "x-signature-algorithm": "HMAC-SHA256",
        "x-signature-nonce": "48ef5afed43d4d91ae514aaeafbc29ba",
        "x-signature-version": "1.0",
        "x-timestamp": "2022-01-04T03:55:31Z",
    }
    actual = generate_signature(
        path=path,
        query_params=query,
        body=body,
        app_key=headers["x-app-key"],
        app_secret="0f50a2e853334a9aae1a783bee120c1f",
        host=headers["host"],
        timestamp=headers["x-timestamp"],
        nonce=headers["x-signature-nonce"],
    )
    # The page publishes this exact result, but its displayed 32-character
    # digest is MD5, not SHA256. Keep the inconsistency visible and never treat
    # the published value as the runtime result.
    published_signature = "kvlS6opdZDhEBo5jq40nHYXaLvM="
    assert actual == "mafoLh6ZyyaOs0UAHUagoSH2yXTDzlkRUuCR/Xjo7UE="
    assert actual != published_signature
    assert documented_sha256 == "08B9F294222127D6BA471D2A53634393B4FB8E8F038B09183AF6B2164F610C08"
    assert published_worked_example_digest == "E296C96787E1A309691CEF3692F5EEDD"
    assert published_worked_example_digest != documented_sha256


def make_client(handler, **kwargs):
    return WebullClient(
        "app-key",
        "app-secret",
        host="api.webull.co.th",
        http_client=httpx.Client(
            base_url="https://api.webull.co.th", transport=httpx.MockTransport(handler)
        ),
        timestamp_factory=lambda: "2025-01-02T03:04:05Z",
        nonce_factory=lambda: "fixed-nonce",
        **kwargs,
    )


def test_get_signing_and_json_response() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.path == "/openapi/account/list"
        assert request.url.params["region_id"] == "th"
        assert request.headers["x-app-key"] == "app-key"
        assert request.headers["x-signature-algorithm"] == "HMAC-SHA256"
        assert request.headers["x-version"] == "v2"
        assert request.headers["x-signature"]
        assert "app-secret" not in str(request.headers).lower()
        return httpx.Response(200, json={"ok": True})

    with make_client(handler) as client:
        assert client.request("GET", "/openapi/account/list", query={"region_id": "th"}) == {"ok": True}


def test_json_body_is_signed_as_the_sent_bytes() -> None:
    body = b'{"symbol":"AAPL","qty":1}'

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.content == body
        assert request.headers["content-type"] == "application/json"
        expected = generate_signature(
            path=request.url.path,
            query_params={},
            body=body,
            app_key="app-key",
            app_secret="app-secret",
            host="api.webull.co.th",
            timestamp="2025-01-02T03:04:05Z",
            nonce="fixed-nonce",
        )
        assert request.headers["x-signature"] == expected
        return httpx.Response(200, json={"accepted": True})

    with make_client(handler) as client:
        assert client.request(
            "POST",
            "/openapi/trade/order/preview",
            body=body,
            allow_write=True,
            write_confirmation="PREVIEW",
        ) == {"accepted": True}


def test_batch_bars_post_is_read_only_and_bypasses_write_gate() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.method == "POST"
        assert request.url.path == "/openapi/market-data/stock/batch-bars"
        return httpx.Response(200, json={"bars": []})

    with make_client(handler) as client:
        assert client.request(
            "POST",
            "/openapi/market-data/stock/batch-bars",
            body=b'{"symbols":["AAPL"]}',
        ) == {"bars": []}


def test_token_check_post_is_cataloged_read() -> None:
    with make_client(lambda request: httpx.Response(200, json={"active": True})) as client:
        assert client.request("POST", "/openapi/auth/token/check", body=b"{}") == {"active": True}


def test_unknown_endpoint_fails_closed_before_network() -> None:
    called = False

    def handler(request):
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with make_client(handler) as client:
        with pytest.raises(EndpointNotAllowedError):
            client.request("POST", "/openapi/not-in-catalog")
    assert not called


@pytest.mark.parametrize("host", ["evil.example", "api.webull.co.th.evil", "https://api.webull.co.th"])
def test_host_allowlist_rejects_arbitrary_hosts(host) -> None:
    with pytest.raises(ValueError):
        WebullClient("app", "secret", host=host)


def test_env_host_selection_is_exact(monkeypatch) -> None:
    monkeypatch.setenv("WEBULL_APP_KEY", "app")
    monkeypatch.setenv("WEBULL_APP_SECRET", "secret")
    monkeypatch.setenv("WEBULL_ENV", "uat")
    monkeypatch.delenv("WEBULL_API_HOST", raising=False)
    client = WebullClient.from_env(
        http_client=httpx.Client(
            base_url="https://th-api.uat.webullbroker.com",
            transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})),
        )
    )
    assert client.host == "th-api.uat.webullbroker.com"
    client.close()


def test_env_loading_ignores_legacy_api_key_and_does_not_leak(monkeypatch) -> None:
    monkeypatch.setenv("WEBULL_APP_KEY", "env-app")
    monkeypatch.setenv("WEBULL_APP_SECRET", "env-secret")
    monkeypatch.setenv("WEBULL_ACCESS_TOKEN", "env-token")
    monkeypatch.setenv("WEBULL_API_KEY", "legacy-must-not-be-used")
    monkeypatch.setenv("WEBULL_TIMEOUT_SECONDS", "7")
    client = WebullClient.from_env(
        http_client=httpx.Client(
            base_url="https://api.webull.co.th", transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
        )
    )
    assert client.app_key == "env-app"
    assert client.app_secret == "env-secret"
    assert client.access_token == "env-token"
    assert client.timeout == 7.0
    assert "legacy-must-not-be-used" not in repr(client.__dict__)
    client.close()


@pytest.mark.parametrize(
    ("method", "path", "confirmation"),
    [
        ("POST", "/openapi/trade/order/place", "PLACE"),
        ("POST", "/openapi/market-data/watchlist/create", "WATCHLIST_WRITE"),
        ("POST", "/openapi/auth/token/create", "TOKEN_WRITE"),
    ],
)
def test_write_confirmation_gates(method, path, confirmation) -> None:
    called = False

    def handler(request):
        nonlocal called
        called = True
        return httpx.Response(200, json={})

    with make_client(handler) as client:
        with pytest.raises(WriteConfirmationError):
            client.request(method, path)
        with pytest.raises(WriteConfirmationError):
            client.request(method, path, allow_write=True, write_confirmation="PLACE" if confirmation != "PLACE" else "CANCEL")
        assert not called
        assert client.request(
            method,
            path,
            allow_write=True,
            write_confirmation=confirmation,
        ) == {}


def test_redacted_http_errors_preserve_status_without_body() -> None:
    secret_body = {"access_token": "do-not-print", "app_secret": "also-do-not-print"}

    def handler(request):
        return httpx.Response(401, json=secret_body)

    with make_client(handler) as client:
        with pytest.raises(WebullAPIError) as caught:
            client.request("GET", "/openapi/account/list")
    assert caught.value.status_code == 401
    message = str(caught.value)
    assert "401" in message
    assert "do-not-print" not in message
    assert "also-do-not-print" not in message


def test_cli_rejects_argv_secret_flags() -> None:
    with pytest.raises(SystemExit):
        build_parser().parse_args(["request", "--method", "GET", "--path", "/openapi/account/list", "--access-token", "secret"])
    with pytest.raises(SystemExit):
        build_parser().parse_args(["request", "--method", "POST", "--path", "/openapi/auth/token/check", "--body-json", "{}"])


def test_cli_body_file_and_default_recursive_redaction(monkeypatch, tmp_path, capsys) -> None:
    body_path = tmp_path / "body.json"
    body_path.write_bytes(b'{"symbol":"AAPL"}')
    monkeypatch.setenv("WEBULL_APP_KEY", "app")
    monkeypatch.setenv("WEBULL_APP_SECRET", "secret")
    client = make_client(lambda request: httpx.Response(200, json={
        "access_token": "token-value",
        "nested": [{"app_key": "key-value", "ok": True}],
        "signature": "sig-value",
    }))
    monkeypatch.setattr(WebullClient, "from_env", classmethod(lambda cls, **kwargs: client))
    assert main(["request", "--method", "POST", "--path", "/openapi/auth/token/check", "--body-file", str(body_path)]) == 0
    output = capsys.readouterr().out
    assert "token-value" not in output
    assert "key-value" not in output
    assert "sig-value" not in output
    assert "[REDACTED]" in output


def test_cli_body_stdin(monkeypatch, capsys) -> None:
    monkeypatch.setenv("WEBULL_APP_KEY", "app")
    monkeypatch.setenv("WEBULL_APP_SECRET", "secret")
    client = make_client(lambda request: httpx.Response(200, json={"ok": True}))
    monkeypatch.setattr(WebullClient, "from_env", classmethod(lambda cls, **kwargs: client))
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b'{"active":true}')))
    assert main(["request", "--method", "POST", "--path", "/openapi/auth/token/check", "--body-stdin"]) == 0
    assert capsys.readouterr().out.strip() == '{"ok":true}'
