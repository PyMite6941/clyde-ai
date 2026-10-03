#!/usr/bin/env python3
"""
Build a tool-use training dataset for MCP, Google plugins, and similar tools.

Writes JSONL examples under data/tools/training/ and verifies official
reference URLs (no article scraping).
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from scraper import USER_AGENT, RateLimiter, log

# Official / public reference URLs for tool ecosystems (docs only).
REFERENCE_URLS: list[dict[str, str]] = [
    {
        "id": "mcp_docs",
        "category": "mcp",
        "url": "https://modelcontextprotocol.io/",
        "title": "Model Context Protocol docs",
    },
    {
        "id": "mcp_spec_github",
        "category": "mcp",
        "url": "https://github.com/modelcontextprotocol/specification",
        "title": "MCP specification repository",
    },
    {
        "id": "mcp_python_sdk",
        "category": "mcp",
        "url": "https://github.com/modelcontextprotocol/python-sdk",
        "title": "MCP Python SDK",
    },
    {
        "id": "google_plugins_workspace",
        "category": "google_plugins",
        "url": "https://developers.google.com/workspace/add-ons/overview",
        "title": "Google Workspace Add-ons overview",
    },
    {
        "id": "google_apps_script",
        "category": "google_plugins",
        "url": "https://developers.google.com/apps-script",
        "title": "Google Apps Script",
    },
    {
        "id": "google_gemini_extensions",
        "category": "google_plugins",
        "url": "https://ai.google.dev/gemini-api/docs/function-calling",
        "title": "Gemini function calling",
    },
    {
        "id": "openai_function_calling",
        "category": "function_calling",
        "url": "https://platform.openai.com/docs/guides/function-calling",
        "title": "OpenAI function calling guide",
    },
]


def _tool_schema(name: str, description: str, properties: dict[str, Any], required: list[str] | None = None) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": required or [],
            },
        },
    }


def _example(
    *,
    example_id: str,
    category: str,
    tools: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    notes: str = "",
) -> dict[str, Any]:
    return {
        "id": example_id,
        "category": category,
        "notes": notes,
        "tools": tools,
        "messages": messages,
    }


def build_examples() -> list[dict[str, Any]]:
    """Curated tool-use dialogues for training (MCP, Google plugins, etc.)."""
    examples: list[dict[str, Any]] = []

    # --- MCP ---
    mcp_tools = [
        _tool_schema(
            "mcp_list_tools",
            "List tools exposed by a connected MCP server.",
            {
                "server": {"type": "string", "description": "MCP server id or name"},
            },
            ["server"],
        ),
        _tool_schema(
            "mcp_call_tool",
            "Call a tool on an MCP server with JSON arguments.",
            {
                "server": {"type": "string"},
                "tool": {"type": "string"},
                "arguments": {"type": "object"},
            },
            ["server", "tool"],
        ),
        _tool_schema(
            "mcp_read_resource",
            "Read a resource URI from an MCP server.",
            {
                "server": {"type": "string"},
                "uri": {"type": "string"},
            },
            ["server", "uri"],
        ),
    ]

    examples.append(
        _example(
            example_id="mcp_list_then_call",
            category="mcp",
            tools=mcp_tools,
            notes="Discover MCP tools then invoke one.",
            messages=[
                {
                    "role": "user",
                    "content": "Using the filesystem MCP server, list available tools then read README.md from the project root.",
                },
                {
                    "role": "assistant",
                    "content": "I'll list the filesystem MCP tools first.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "mcp_list_tools",
                                "arguments": json.dumps({"server": "filesystem"}),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "mcp_list_tools",
                    "content": json.dumps(
                        {
                            "tools": [
                                {"name": "list_directory", "description": "List a directory"},
                                {"name": "read_file", "description": "Read a text file"},
                            ]
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": "Next I'll read README.md.",
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "mcp_call_tool",
                                "arguments": json.dumps(
                                    {
                                        "server": "filesystem",
                                        "tool": "read_file",
                                        "arguments": {"path": "README.md"},
                                    }
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_2",
                    "name": "mcp_call_tool",
                    "content": json.dumps({"content": "# Project\nTraining data pipeline.\n"}),
                },
                {
                    "role": "assistant",
                    "content": "README.md starts with '# Project' and describes a training data pipeline.",
                },
            ],
        )
    )

    examples.append(
        _example(
            example_id="mcp_resource_uri",
            category="mcp",
            tools=mcp_tools,
            notes="Read an MCP resource by URI.",
            messages=[
                {
                    "role": "user",
                    "content": "From the docs MCP server, open resource docs://mcp/overview.",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "mcp_read_resource",
                                "arguments": json.dumps(
                                    {"server": "docs", "uri": "docs://mcp/overview"}
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "mcp_read_resource",
                    "content": json.dumps(
                        {
                            "uri": "docs://mcp/overview",
                            "mimeType": "text/markdown",
                            "text": "MCP connects hosts to tools and resources via servers.",
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": "MCP connects hosts to tools and resources through servers.",
                },
            ],
        )
    )

    # --- Google plugins / Workspace ---
    google_tools = [
        _tool_schema(
            "google_gmail_search",
            "Search Gmail messages with a query string.",
            {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            ["query"],
        ),
        _tool_schema(
            "google_calendar_list_events",
            "List upcoming Google Calendar events.",
            {
                "calendar_id": {"type": "string", "default": "primary"},
                "max_results": {"type": "integer", "default": 5},
            },
            [],
        ),
        _tool_schema(
            "google_drive_search",
            "Search Google Drive files by name or content.",
            {
                "query": {"type": "string"},
                "mime_type": {"type": "string"},
            },
            ["query"],
        ),
        _tool_schema(
            "google_sheets_read",
            "Read a range from a Google Sheet.",
            {
                "spreadsheet_id": {"type": "string"},
                "range": {"type": "string"},
            },
            ["spreadsheet_id", "range"],
        ),
    ]

    examples.append(
        _example(
            example_id="google_gmail_then_calendar",
            category="google_plugins",
            tools=google_tools,
            notes="Multi-plugin workflow across Gmail and Calendar.",
            messages=[
                {
                    "role": "user",
                    "content": "Find unread emails about 'invoice' and list my next 3 calendar events.",
                },
                {
                    "role": "assistant",
                    "content": "I'll search Gmail and list calendar events.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "google_gmail_search",
                                "arguments": json.dumps(
                                    {"query": "is:unread invoice", "max_results": 5}
                                ),
                            },
                        },
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "google_calendar_list_events",
                                "arguments": json.dumps(
                                    {"calendar_id": "primary", "max_results": 3}
                                ),
                            },
                        },
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "google_gmail_search",
                    "content": json.dumps(
                        {
                            "messages": [
                                {"id": "m1", "subject": "Invoice #442", "from": "billing@acme.test"}
                            ]
                        }
                    ),
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_2",
                    "name": "google_calendar_list_events",
                    "content": json.dumps(
                        {
                            "events": [
                                {"summary": "Standup", "start": "2026-09-30T10:00:00+07:00"},
                                {"summary": "Design review", "start": "2026-09-30T14:00:00+07:00"},
                            ]
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": (
                        "Unread invoice mail: 'Invoice #442' from billing@acme.test. "
                        "Next events: Standup at 10:00 and Design review at 14:00 (local)."
                    ),
                },
            ],
        )
    )

    examples.append(
        _example(
            example_id="google_drive_sheets",
            category="google_plugins",
            tools=google_tools,
            notes="Find a sheet in Drive then read a range.",
            messages=[
                {
                    "role": "user",
                    "content": "Find the spreadsheet named Q3 Budget and read sheet Data!A1:B5.",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "google_drive_search",
                                "arguments": json.dumps(
                                    {
                                        "query": "name = 'Q3 Budget'",
                                        "mime_type": "application/vnd.google-apps.spreadsheet",
                                    }
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "google_drive_search",
                    "content": json.dumps({"files": [{"id": "sheet_123", "name": "Q3 Budget"}]}),
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "google_sheets_read",
                                "arguments": json.dumps(
                                    {"spreadsheet_id": "sheet_123", "range": "Data!A1:B5"}
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_2",
                    "name": "google_sheets_read",
                    "content": json.dumps(
                        {"values": [["Item", "Amount"], ["Cloud", "1200"], ["Tools", "350"]]}
                    ),
                },
                {
                    "role": "assistant",
                    "content": "Q3 Budget Data!A1:B5 shows Cloud 1200 and Tools 350.",
                },
            ],
        )
    )

    # --- Generic plugins / browser / web ---
    plugin_tools = [
        _tool_schema(
            "web_search",
            "Search the public web for a query.",
            {"query": {"type": "string"}, "num_results": {"type": "integer", "default": 5}},
            ["query"],
        ),
        _tool_schema(
            "http_get",
            "GET a URL and return status plus truncated body text.",
            {"url": {"type": "string"}, "max_chars": {"type": "integer", "default": 2000}},
            ["url"],
        ),
        _tool_schema(
            "browser_open",
            "Open a page in a headless browser and return title/text snapshot.",
            {"url": {"type": "string"}},
            ["url"],
        ),
    ]

    examples.append(
        _example(
            example_id="plugin_web_then_fetch",
            category="plugins",
            tools=plugin_tools,
            notes="Search then fetch a documentation page.",
            messages=[
                {
                    "role": "user",
                    "content": "Find the official MCP docs site and summarize the homepage title.",
                },
                {
                    "role": "assistant",
                    "content": "I'll search, then open the official docs URL.",
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "web_search",
                                "arguments": json.dumps(
                                    {"query": "Model Context Protocol official docs", "num_results": 3}
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "web_search",
                    "content": json.dumps(
                        {
                            "results": [
                                {
                                    "title": "Model Context Protocol",
                                    "url": "https://modelcontextprotocol.io/",
                                }
                            ]
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_2",
                            "type": "function",
                            "function": {
                                "name": "http_get",
                                "arguments": json.dumps(
                                    {"url": "https://modelcontextprotocol.io/", "max_chars": 500}
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_2",
                    "name": "http_get",
                    "content": json.dumps(
                        {"status": 200, "title": "Model Context Protocol", "body_preview": "MCP..."}
                    ),
                },
                {
                    "role": "assistant",
                    "content": "The official docs are at modelcontextprotocol.io (HTTP 200).",
                },
            ],
        )
    )

    # --- Refusal / no-tool path ---
    examples.append(
        _example(
            example_id="no_tool_needed",
            category="control",
            tools=plugin_tools,
            notes="Answer without tools when not required.",
            messages=[
                {
                    "role": "user",
                    "content": "In one sentence, what is an MCP server?",
                },
                {
                    "role": "assistant",
                    "content": (
                        "An MCP server is a process that exposes tools and resources "
                        "to an AI host over the Model Context Protocol."
                    ),
                },
            ],
        )
    )

    # --- File pipeline tool ---
    file_tools = [
        _tool_schema(
            "pipeline_process_file",
            "Run a file through the local input/output processing pipeline.",
            {
                "input_path": {"type": "string"},
                "operation": {
                    "type": "string",
                    "enum": ["normalize", "validate", "to_jsonl", "manifest"],
                },
            },
            ["input_path", "operation"],
        )
    ]
    examples.append(
        _example(
            example_id="pipeline_normalize",
            category="file_pipeline",
            tools=file_tools,
            notes="Invoke local file processing pipeline.",
            messages=[
                {
                    "role": "user",
                    "content": "Normalize data/pipeline/input/sample.jsonl for training output.",
                },
                {
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [
                        {
                            "id": "call_1",
                            "type": "function",
                            "function": {
                                "name": "pipeline_process_file",
                                "arguments": json.dumps(
                                    {
                                        "input_path": "data/pipeline/input/sample.jsonl",
                                        "operation": "normalize",
                                    }
                                ),
                            },
                        }
                    ],
                },
                {
                    "role": "tool",
                    "tool_call_id": "call_1",
                    "name": "pipeline_process_file",
                    "content": json.dumps(
                        {
                            "ok": True,
                            "output_path": "data/pipeline/output/sample.normalized.jsonl",
                            "records": 3,
                        }
                    ),
                },
                {
                    "role": "assistant",
                    "content": "Normalized 3 records to data/pipeline/output/sample.normalized.jsonl.",
                },
            ],
        )
    )

    return examples


class ToolsDatasetBuilder:
    def __init__(self, base_dir: str | Path = "data", timeout: float = 30.0) -> None:
        self.base_dir = Path(base_dir)
        self.out_dir = self.base_dir / "tools" / "training"
        self.out_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.limiter = RateLimiter(min_interval=1.5, cooldown_429=60.0)

    def ping_url(self, url: str) -> dict[str, Any]:
        self.limiter.wait()
        try:
            response = self.session.head(url, timeout=self.timeout, allow_redirects=True)
            if response.status_code in (403, 405) or response.status_code >= 400:
                self.limiter.wait()
                response = self.session.get(url, timeout=self.timeout, allow_redirects=True, stream=True)
                # drain minimally
                response.close()
            ok = 200 <= response.status_code < 400
            return {
                "url": url,
                "ok": ok,
                "status_code": response.status_code,
                "error": None if ok else f"HTTP {response.status_code}",
            }
        except requests.RequestException as exc:
            return {"url": url, "ok": False, "status_code": None, "error": str(exc)}

    def verify_references(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for item in REFERENCE_URLS:
            log(f"[tools] ping {item['id']}: {item['url']}")
            ping = self.ping_url(item["url"])
            record = {**item, "ping": ping}
            results.append(record)
            if ping["ok"]:
                log(f"  OK {ping['status_code']}")
            else:
                log(f"  FAIL {ping.get('status_code')} {ping.get('error')}")
        return results

    def build(self, verify_links: bool = True) -> dict[str, Any]:
        examples = build_examples()
        jsonl_path = self.out_dir / "tool_use_train.jsonl"
        with jsonl_path.open("w", encoding="utf-8") as handle:
            for ex in examples:
                handle.write(json.dumps(ex, ensure_ascii=False) + "\n")

        schema_path = self.out_dir / "tool_schemas.json"
        schemas = {
            "categories": sorted({ex["category"] for ex in examples}),
            "example_count": len(examples),
            "format": "openai_style_tool_calls_jsonl",
            "fields": ["id", "category", "notes", "tools", "messages"],
        }
        schema_path.write_text(json.dumps(schemas, indent=2), encoding="utf-8")

        references: list[dict[str, Any]] = []
        if verify_links:
            references = self.verify_references()

        ok_refs = [r for r in references if r.get("ping", {}).get("ok")]
        fail_refs = [r for r in references if not r.get("ping", {}).get("ok")]
        manifest = {
            "kind": "tools_training_dataset",
            "scraped_info": False,
            "examples_path": str(jsonl_path),
            "schema_path": str(schema_path),
            "example_count": len(examples),
            "categories": schemas["categories"],
            "references_ok": ok_refs,
            "references_failed": fail_refs,
            "summary": {
                "examples": len(examples),
                "refs_ok": len(ok_refs),
                "refs_failed": len(fail_refs),
            },
        }
        manifest_path = self.out_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
        log(
            f"[tools] wrote {jsonl_path} ({len(examples)} examples); "
            f"refs ok={len(ok_refs)} failed={len(fail_refs)}"
        )
        return manifest


if __name__ == "__main__":
    verify = "--skip-verify" not in sys.argv
    builder = ToolsDatasetBuilder()
    result = builder.build(verify_links=verify)
    if result["summary"]["examples"] == 0:
        sys.exit(1)
    if verify and result["summary"]["refs_ok"] == 0:
        sys.exit(1)
