#!/usr/bin/env python3
"""
Download verified Wikipedia / Wikimedia Commons language media, build the
tools training dataset (MCP / Google plugins / etc.), and run the file
processing pipeline (input -> staging -> output).

Usage:
    python scraper.py
    python downloader.py

    python downloader.py en,fr 3
    python downloader.py --tools-only
    python downloader.py --pipeline-only
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlparse

import requests

from pipeline import FileProcessingPipeline
from scraper import USER_AGENT, WikipediaMediaScraper
from tools_dataset import ToolsDatasetBuilder

SAFE_NAME = re.compile(r"[^\w.\-()+ ]+", re.UNICODE)


def log(msg: str) -> None:
    print(msg, flush=True)


class MediaDownloader:
    def __init__(self, base_dir: str | Path = "data", chunk_size: int = 64 * 1024) -> None:
        self.base_dir = Path(base_dir)
        self.media_root = self.base_dir / "language" / "wikipedia_media"
        self.chunk_size = chunk_size

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})
        self.scraper = WikipediaMediaScraper(base_dir=self.base_dir)

    @staticmethod
    def _filename_from_item(item: dict[str, Any]) -> str:
        title = item.get("title") or ""
        if title.startswith("File:"):
            name = title[5:]
        else:
            path = urlparse(item["url"]).path
            name = unquote(Path(path).name)
        name = SAFE_NAME.sub("_", name).strip().replace(" ", "_")
        return name or "media.bin"

    def download_file(self, url: str, destination: Path) -> bool:
        if destination.exists() and destination.stat().st_size > 0:
            log(f"  already exists: {destination.name}")
            return True

        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_suffix(destination.suffix + ".part")

        for attempt in range(1, 4):
            self.scraper.cdn_limiter.wait()
            try:
                with self.session.get(
                    url, stream=True, timeout=120, allow_redirects=True
                ) as response:
                    if response.status_code == 429:
                        self.scraper.cdn_limiter.penalize()
                        continue
                    response.raise_for_status()
                    with open(partial, "wb") as handle:
                        for chunk in response.iter_content(chunk_size=self.chunk_size):
                            if chunk:
                                handle.write(chunk)
                if partial.stat().st_size <= 0:
                    partial.unlink(missing_ok=True)
                    log("  download produced empty file")
                    return False
                partial.replace(destination)
                log(
                    f"  saved {destination.name} "
                    f"({destination.stat().st_size} bytes)"
                )
                return True
            except Exception as exc:
                if partial.exists():
                    partial.unlink(missing_ok=True)
                log(f"  download failed ({attempt}/3): {exc}")
                time.sleep(5)
        return False

    def load_manifest(self, path: Path | None = None) -> dict[str, Any]:
        path = path or (self.media_root / "manifest.json")
        if not path.exists():
            raise FileNotFoundError(
                f"Manifest not found: {path}. Run scraper.py first."
            )
        return json.loads(path.read_text(encoding="utf-8"))

    def download_verified(
        self,
        languages: list[str] | None = None,
        re_ping: bool = True,
    ) -> dict[str, Any]:
        """Re-verify then download only media entries that pass."""
        manifest = self.load_manifest()
        report: dict[str, Any] = {
            "downloaded": 0,
            "skipped": 0,
            "failed": 0,
            "by_language": {},
        }

        lang_map: dict[str, Any] = manifest.get("languages", {})
        selected = languages or list(lang_map.keys())

        for lang in selected:
            entry = lang_map.get(lang)
            if not entry:
                log(f"[{lang}] not in manifest; skip")
                continue

            verified = entry.get("verified") or []
            lang_manifest_path = entry.get("manifest_path")
            if lang_manifest_path and Path(lang_manifest_path).exists():
                local = json.loads(
                    Path(lang_manifest_path).read_text(encoding="utf-8")
                )
                verified = local.get("verified") or verified

            out_dir = self.media_root / lang / "files"
            out_dir.mkdir(parents=True, exist_ok=True)
            lang_stats = {"downloaded": 0, "skipped": 0, "failed": 0}

            log(f"[{lang}] {len(verified)} verified media candidate(s)")
            for item in verified:
                url = item.get("url")
                title = item.get("title")
                if not url:
                    lang_stats["failed"] += 1
                    report["failed"] += 1
                    continue

                if re_ping:
                    ping = (
                        self.scraper.ping_api(title, url)
                        if title
                        else self.scraper.ping(url)
                    )
                    if not ping["ok"]:
                        log(
                            f"[{lang}] ping failed for {title}: "
                            f"{ping.get('error')}"
                        )
                        lang_stats["failed"] += 1
                        report["failed"] += 1
                        continue
                    log(f"[{lang}] ping OK {title}")

                dest = out_dir / self._filename_from_item(item)
                if dest.exists() and dest.stat().st_size > 0:
                    lang_stats["skipped"] += 1
                    report["skipped"] += 1
                    log(f"[{lang}] skip existing {dest.name}")
                    continue

                log(f"[{lang}] download {title}")
                if self.download_file(url, dest):
                    lang_stats["downloaded"] += 1
                    report["downloaded"] += 1
                else:
                    lang_stats["failed"] += 1
                    report["failed"] += 1

            report["by_language"][lang] = lang_stats
            log(
                f"[{lang}] done: downloaded={lang_stats['downloaded']} "
                f"skipped={lang_stats['skipped']} failed={lang_stats['failed']}"
            )

        report_path = self.media_root / "download_report.json"
        report_path.write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        log(f"Report: {report_path}")
        return report


def ensure_manifest(
    languages: list[str],
    per_language: int,
    base_dir: str | Path = "data",
) -> None:
    media_root = Path(base_dir) / "language" / "wikipedia_media"
    root = media_root / "manifest.json"
    if root.exists():
        return
    log("No manifest found; running scraper first...")
    scraper = WikipediaMediaScraper(base_dir=base_dir)
    scraper.scrape_language_media(languages=languages, per_language=per_language)


def build_tools_dataset(base_dir: str | Path = "data", verify_links: bool = True) -> dict[str, Any]:
    log("Building tools training dataset (MCP / Google plugins / ...)")
    return ToolsDatasetBuilder(base_dir=base_dir).build(verify_links=verify_links)


def run_file_pipeline(base_dir: str | Path = "data", operation: str = "normalize") -> dict[str, Any]:
    log("Running file processing pipeline (input -> staging -> output)")
    pipeline = FileProcessingPipeline(base_dir=base_dir)
    pipeline.seed_sample_input()
    return pipeline.run(operation=operation, ingest_defaults=True)


if __name__ == "__main__":
    languages = ["en", "es", "fr", "de", "zh", "id"]
    per_language = 5
    tools_only = "--tools-only" in sys.argv
    pipeline_only = "--pipeline-only" in sys.argv
    skip_media = "--skip-media" in sys.argv or tools_only or pipeline_only
    skip_tools = "--skip-tools" in sys.argv or pipeline_only
    skip_pipeline = "--skip-pipeline" in sys.argv or tools_only
    skip_verify_refs = "--skip-verify" in sys.argv

    args = [
        a
        for a in sys.argv[1:]
        if not a.startswith("--")
    ]
    if len(args) > 0:
        languages = args[0].split(",")
    if len(args) > 1:
        per_language = int(args[1])

    media_report: dict[str, Any] | None = None
    tools_report: dict[str, Any] | None = None
    pipeline_report: dict[str, Any] | None = None
    exit_code = 0

    if not skip_media:
        ensure_manifest(languages=languages, per_language=per_language)
        downloader = MediaDownloader()
        media_report = downloader.download_verified(languages=languages, re_ping=True)
        if media_report["failed"] > 0:
            exit_code = 1
            log(f"Media completed with {media_report['failed']} failure(s).")
        else:
            log(
                f"Media OK. downloaded={media_report['downloaded']} "
                f"skipped={media_report['skipped']}"
            )

    if not skip_tools:
        tools_report = build_tools_dataset(verify_links=not skip_verify_refs)
        if tools_report["summary"]["examples"] == 0:
            exit_code = 1
        if (
            not skip_verify_refs
            and tools_report["summary"]["refs_failed"] > 0
            and tools_report["summary"]["refs_ok"] == 0
        ):
            exit_code = 1

    if not skip_pipeline:
        pipeline_report = run_file_pipeline()
        if pipeline_report["failed"] > 0 and pipeline_report["ok"] == 0:
            exit_code = 1

    summary = {
        "media": media_report,
        "tools": {
            "examples": (tools_report or {}).get("summary", {}).get("examples"),
            "refs_ok": (tools_report or {}).get("summary", {}).get("refs_ok"),
            "refs_failed": (tools_report or {}).get("summary", {}).get("refs_failed"),
            "path": (tools_report or {}).get("examples_path"),
        }
        if tools_report
        else None,
        "pipeline": {
            "ok": (pipeline_report or {}).get("ok"),
            "failed": (pipeline_report or {}).get("failed"),
            "training_pack": (pipeline_report or {}).get("training_pack"),
            "training_pack_records": (pipeline_report or {}).get("training_pack_records"),
        }
        if pipeline_report
        else None,
    }
    summary_path = Path("data") / "run_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    log(f"Summary: {summary_path}")
    sys.exit(exit_code)
