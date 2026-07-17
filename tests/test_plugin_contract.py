"""Deterministic contract checks for the public Webull OpenAPI plugin."""

from __future__ import annotations

import json
import re
from pathlib import Path
import tomllib


ROOT = Path(__file__).resolve().parents[1]


def test_required_plugin_surface_exists() -> None:
    assert (ROOT / ".claude-plugin/plugin.json").is_file()
    assert (ROOT / ".codex-plugin/plugin.json").is_file()
    assert (ROOT / "scripts/webull_api.py").is_file()
    assert (ROOT / "references/endpoints.json").is_file()
    assert (ROOT / "references/authentication.md").is_file()


def test_manifests_are_valid_json_and_reference_the_skill() -> None:
    for relative_path in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json"):
        manifest = json.loads((ROOT / relative_path).read_text(encoding="utf-8"))
        assert manifest["name"] == "webull-openapi"
        assert manifest["version"] == "0.2.0"

    claude_manifest = json.loads(
        (ROOT / ".claude-plugin/plugin.json").read_text(encoding="utf-8")
    )
    codex_manifest = json.loads(
        (ROOT / ".codex-plugin/plugin.json").read_text(encoding="utf-8")
    )
    assert len(claude_manifest["skills"]) == 6
    assert sorted(Path(item).name for item in claude_manifest["skills"]) == sorted(
        path.parent.name for path in (ROOT / "skills").glob("*/SKILL.md")
    )
    assert codex_manifest["skills"] == "./skills/"


def test_endpoint_catalog_and_auth_reference_contract() -> None:
    catalog = json.loads((ROOT / "references/endpoints.json").read_text(encoding="utf-8"))
    entries = catalog["entries"]
    assert sum(entry["transport"] == "http" for entry in entries) == 34
    assert sum(entry["transport"] == "mqtt" for entry in entries) == 1
    assert sum(entry["transport"] == "grpc" for entry in entries) == 1
    assert all(entry["docs_url"].startswith("https://developer.webull.co.th/") for entry in entries)
    assert "/openapi/market-data/stock/batch-bars" in {
        entry["path"] for entry in entries if entry["path"]
    }
    by_key = {(entry["method"], entry["path"]): entry for entry in entries if entry["path"]}
    assert by_key[("POST", "/openapi/auth/token/check")]["risk"] == "read"
    assert by_key[("POST", "/openapi/market-data/stock/batch-bars")]["risk"] == "read"
    assert by_key[("POST", "/openapi/auth/token/create")]["confirmation"] == "TOKEN_WRITE"
    assert by_key[("POST", "/openapi/market-data/streaming/subscribe")]["confirmation"] == "STREAMING"
    assert (ROOT / "references/authentication.md").read_text(encoding="utf-8").strip()


def test_python_package_contract() -> None:
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["name"] == "webull-openapi"
    assert project["project"]["version"] == "0.2.0"
    assert project["project"]["scripts"]["webull-api"] == "scripts.webull_api:main"
    assert "scripts*" in project["tool"]["setuptools"]["packages"]["find"]["include"]


def test_plugin_surface_contains_no_obvious_real_secrets() -> None:
    files = list((ROOT / ".claude-plugin").glob("*.json"))
    files += list((ROOT / ".codex-plugin").glob("*.json"))
    files += list((ROOT / "skills").glob("*/SKILL.md"))
    files += [ROOT / "scripts/webull_api.py", ROOT / "references/authentication.md"]
    text = "\n".join(path.read_text(encoding="utf-8") for path in files)
    suspicious_patterns = (
        r"(?i)\bsk-[a-z0-9]{16,}\b",
        r"\bAKIA[0-9A-Z]{16}\b",
        r"(?i)\beyJ[a-z0-9_-]{20,}\.[a-z0-9_-]{10,}\.[a-z0-9_-]{10,}\b",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
        r"(?i)\b(?:xoxb|xoxp)-[0-9A-Za-z-]{16,}\b",
        r"(?i)\b(?:api[_ -]?key|app[_ -]?key|app[_ -]?secret|access[_ -]?token)\s*[:=]\s*['\"][^'\"]{8,}['\"]",
    )
    for pattern in suspicious_patterns:
        assert re.search(pattern, text) is None, f"possible secret matched: {pattern}"
