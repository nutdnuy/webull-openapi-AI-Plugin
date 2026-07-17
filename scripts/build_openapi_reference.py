"""Build the checked-in OpenAPI-style reference from downloaded Webull pages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path


HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}


def load_leaf(page: Path) -> dict:
    match = re.search(r"```json\s*\n(.*?)\n```", page.read_text(encoding="utf-8"), re.DOTALL)
    if not match:
        raise ValueError(f"no OpenAPI JSON block in {page}")
    definition = json.loads(match.group(1))
    if definition.get("method", "").lower() not in HTTP_METHODS:
        raise ValueError(f"unsupported HTTP method in {page}")
    if not definition.get("path"):
        raise ValueError(f"missing path in {page}")
    return definition


def build(source_dir: Path, catalog_path: Path, output_path: Path) -> None:
    catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
    http_entries = [entry for entry in catalog["entries"] if entry["transport"] == "http"]
    pages = {page.stem: page for page in source_dir.glob("*.md")}
    definitions = {}
    for entry in http_entries:
        slug = entry["docs_url"].rstrip("/").rsplit("/", 1)[-1]
        definition = load_leaf(pages[slug])
        key = (definition["method"].upper(), definition["path"])
        if key != (entry["method"], entry["path"]):
            raise ValueError(f"catalog/source mismatch for {entry['path']}: {key}")
        definitions[key] = (entry, definition)

    first = next(iter(definitions.values()))[1]
    official_info = first["info"]
    document = {
        "openapi": "3.0.3",
        "info": {
            "title": official_info["title"],
            "description": (
                "Consolidated HTTP endpoint schemas extracted from the official Webull "
                "Open API leaf pages. Source: "
                "https://developer.webull.co.th/apis/docs/webull-open-api-reference"
            ),
            "version": official_info["version"],
        },
        "servers": first["servers"],
        "paths": {},
        "x-webull-source": {
            "index_url": "https://developer.webull.co.th/apis/docs/webull-open-api-reference",
            "definition_version": official_info["version"],
            "leaf_page_count": len(definitions),
        },
    }
    for (method, path), (entry, definition) in sorted(definitions.items(), key=lambda item: item[0][1]):
        operation = {
            "summary": entry["title"],
            "tags": definition.get("tags", []),
            "description": definition.get("description", entry.get("description", "")),
            "operationId": definition["operationId"],
            "parameters": definition.get("parameters", []),
            "responses": definition["responses"],
            "x-webull-source-url": entry["docs_url"],
            "x-webull-source": definition,
        }
        if "requestBody" in definition:
            request_body = definition["requestBody"]
            example = definition.get("jsonRequestBodyExample")
            if example is not None:
                request_body = json.loads(json.dumps(request_body))
                request_body.setdefault("content", {}).setdefault("application/json", {})[
                    "example"
                ] = example
            operation["requestBody"] = request_body
        if "jsonRequestBodyExample" in definition:
            operation["x-webull-json-request-body-example"] = definition["jsonRequestBodyExample"]
        if "postman" in definition:
            operation["x-webull-postman"] = definition["postman"]
        document["paths"].setdefault(path, {})[method.lower()] = operation
    output_path.write_text(json.dumps(document, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("source_dir", type=Path)
    parser.add_argument("catalog", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source_dir, args.catalog, args.output)
