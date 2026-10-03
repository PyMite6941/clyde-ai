#!/usr/bin/env python3
"""
Wikipedia / Wikimedia Commons media scraper for language learning material.

Collects pronunciation audio media URLs via the Commons API, verifies every
link through Wikimedia APIs (and optionally the upload CDN), and writes a
manifest of only links that return success.

Does not scrape article text or page info.
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlparse, urlunparse

import requests

USER_AGENT = (
    "AdaptiveSkillLab/1.0 "
    "(educational language media collector; local-dev; python-requests)"
)
COMMONS_API = "https://commons.wikimedia.org/w/api.php"
COMMONS_REST = "https://api.wikimedia.org/core/v1/commons/file"

# Language code -> Commons category of pronunciation media (files only).
LANGUAGE_CATEGORIES: dict[str, str] = {
    "en": "Category:English pronunciation",
    "es": "Category:Spanish pronunciation",
    "fr": "Category:French pronunciation",
    "de": "Category:German pronunciation",
    "zh": "Category:Chinese pronunciation",
    "id": "Category:Indonesian pronunciation",
}

AUDIO_MIME_PREFIXES = ("audio/",)
AUDIO_EXTENSIONS = (".ogg", ".oga", ".opus", ".wav", ".flac", ".mp3", ".webm")


def log(msg: str) -> None:
    print(msg, flush=True)


class RateLimiter:
    """Space outbound requests to stay under Wikimedia rate limits."""

    def __init__(self, min_interval: float = 1.0, cooldown_429: float = 120.0) -> None:
        self.min_interval = min_interval
        self.cooldown_429 = cooldown_429
        self._next_allowed = 0.0

    def wait(self) -> None:
        now = time.monotonic()
        delay = self._next_allowed - now
        if delay > 0:
            time.sleep(delay)
        self._next_allowed = time.monotonic() + self.min_interval

    def penalize(self) -> None:
        log(f"  rate-limited; cooling down {self.cooldown_429:.0f}s")
        time.sleep(self.cooldown_429)
        self._next_allowed = time.monotonic() + self.min_interval


class WikipediaMediaScraper:
    def __init__(
        self,
        base_dir: str | Path = "data",
        timeout: float = 30.0,
        api_interval: float = 1.0,
        cdn_interval: float = 45.0,
        max_retries: int = 3,
        cdn_ping: bool = False,
    ) -> None:
        self.base_dir = Path(base_dir)
        self.language_dir = self.base_dir / "language"
        self.language_dir.mkdir(parents=True, exist_ok=True)

        self.timeout = timeout
        self.max_retries = max_retries
        self.cdn_ping = cdn_ping

        self.api_limiter = RateLimiter(min_interval=api_interval, cooldown_429=60.0)
        self.cdn_limiter = RateLimiter(min_interval=cdn_interval, cooldown_429=120.0)

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT})

    @staticmethod
    def _clean_url(url: str) -> str:
        parsed = urlparse(url)
        return urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))

    @staticmethod
    def _is_audio(title: str, mime: str | None) -> bool:
        if mime and mime.lower().startswith(AUDIO_MIME_PREFIXES):
            return True
        lower = title.lower()
        return any(lower.endswith(ext) for ext in AUDIO_EXTENSIONS)

    def _request(
        self,
        method: str,
        url: str,
        *,
        limiter: RateLimiter,
        params: dict[str, Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> requests.Response:
        last_error: Exception | None = None
        for attempt in range(1, self.max_retries + 1):
            limiter.wait()
            try:
                response = self.session.request(
                    method,
                    url,
                    params=params,
                    headers=headers,
                    timeout=self.timeout,
                    allow_redirects=True,
                )
                if response.status_code == 429:
                    limiter.penalize()
                    continue
                return response
            except requests.RequestException as exc:
                last_error = exc
                log(f"  request error ({attempt}/{self.max_retries}): {exc}")
                time.sleep(5)
        raise RuntimeError(f"Request failed for {url}: {last_error}")

    def _api_get(self, params: dict[str, Any]) -> dict[str, Any]:
        response = self._request("GET", COMMONS_API, limiter=self.api_limiter, params=params)
        response.raise_for_status()
        payload = response.json()
        if "error" in payload:
            raise RuntimeError(payload["error"])
        return payload

    def ping_api(self, title: str, expected_url: str) -> dict[str, Any]:
        """
        Ping Wikimedia APIs for a media file (no article text).
        Confirms the file exists and the original URL is reachable via API.
        """
        clean_expected = self._clean_url(expected_url)
        checks: list[dict[str, Any]] = []

        # 1) MediaWiki imageinfo
        try:
            payload = self._api_get(
                {
                    "action": "query",
                    "format": "json",
                    "titles": title,
                    "prop": "imageinfo",
                    "iiprop": "url|size|mime",
                }
            )
            pages = payload.get("query", {}).get("pages", {})
            page = next(iter(pages.values()), {})
            missing = "missing" in page
            imageinfo = (page.get("imageinfo") or [None])[0]
            api_url = self._clean_url(imageinfo["url"]) if imageinfo and imageinfo.get("url") else None
            ok = (not missing) and api_url == clean_expected
            checks.append(
                {
                    "endpoint": "commons_api_imageinfo",
                    "ok": ok,
                    "status_code": 200,
                    "url": api_url,
                    "error": None if ok else "missing_or_url_mismatch",
                }
            )
        except Exception as exc:
            checks.append(
                {
                    "endpoint": "commons_api_imageinfo",
                    "ok": False,
                    "status_code": None,
                    "url": None,
                    "error": str(exc),
                }
            )

        # 2) Wikimedia REST file endpoint
        rest_url = f"{COMMONS_REST}/{quote(title, safe=':')}"
        try:
            response = self._request("GET", rest_url, limiter=self.api_limiter)
            if response.status_code == 200:
                data = response.json()
                original = data.get("original") or {}
                rest_media = self._clean_url(original["url"]) if original.get("url") else None
                ok = rest_media == clean_expected
                checks.append(
                    {
                        "endpoint": "commons_rest_file",
                        "ok": ok,
                        "status_code": 200,
                        "url": rest_media,
                        "error": None if ok else "url_mismatch",
                    }
                )
            else:
                checks.append(
                    {
                        "endpoint": "commons_rest_file",
                        "ok": False,
                        "status_code": response.status_code,
                        "url": None,
                        "error": f"HTTP {response.status_code}",
                    }
                )
        except Exception as exc:
            checks.append(
                {
                    "endpoint": "commons_rest_file",
                    "ok": False,
                    "status_code": None,
                    "url": None,
                    "error": str(exc),
                }
            )

        # 3) Optional upload CDN probe (slow; often rate-limited)
        if self.cdn_ping:
            try:
                response = self._request(
                    "GET",
                    clean_expected,
                    limiter=self.cdn_limiter,
                    headers={"Range": "bytes=0-0"},
                )
                ok = response.status_code in (200, 206)
                checks.append(
                    {
                        "endpoint": "upload_cdn",
                        "ok": ok,
                        "status_code": response.status_code,
                        "url": clean_expected,
                        "error": None if ok else f"HTTP {response.status_code}",
                    }
                )
            except Exception as exc:
                checks.append(
                    {
                        "endpoint": "upload_cdn",
                        "ok": False,
                        "status_code": None,
                        "url": clean_expected,
                        "error": str(exc),
                    }
                )

        ok = all(c["ok"] for c in checks) and bool(checks)
        return {
            "url": clean_expected,
            "title": title,
            "ok": ok,
            "checks": checks,
            "error": None if ok else "one_or_more_checks_failed",
        }

    # Back-compat alias used by downloader.py
    def ping(self, url: str, title: str | None = None) -> dict[str, Any]:
        if title:
            return self.ping_api(title, url)
        # CDN-only fallback when title is unknown.
        try:
            response = self._request(
                "GET",
                self._clean_url(url),
                limiter=self.cdn_limiter,
                headers={"Range": "bytes=0-0"},
            )
            ok = response.status_code in (200, 206)
            return {
                "url": self._clean_url(url),
                "ok": ok,
                "status_code": response.status_code,
                "content_type": response.headers.get("Content-Type", ""),
                "error": None if ok else f"HTTP {response.status_code}",
            }
        except Exception as exc:
            return {
                "url": self._clean_url(url),
                "ok": False,
                "status_code": None,
                "content_type": "",
                "error": str(exc),
            }

    def _iter_category_files(self, category: str):
        """Yield audio file records from a Commons category (URLs only)."""
        continue_token: str | None = None
        seen: set[str] = set()

        while True:
            params: dict[str, Any] = {
                "action": "query",
                "format": "json",
                "generator": "categorymembers",
                "gcmtitle": category,
                "gcmtype": "file",
                "gcmlimit": 50,
                "prop": "imageinfo",
                "iiprop": "url|size|mime",
            }
            if continue_token:
                params["gcmcontinue"] = continue_token

            payload = self._api_get(params)
            pages = payload.get("query", {}).get("pages", {})
            for page in pages.values():
                title = page.get("title", "")
                if title in seen:
                    continue
                imageinfo = (page.get("imageinfo") or [None])[0]
                if not imageinfo or not imageinfo.get("url"):
                    continue
                mime = imageinfo.get("mime")
                if not self._is_audio(title, mime):
                    continue
                seen.add(title)
                yield {
                    "title": title,
                    "pageid": page.get("pageid"),
                    "url": self._clean_url(imageinfo["url"]),
                    "mime": mime,
                    "size": imageinfo.get("size"),
                }

            continue_token = payload.get("continue", {}).get("gcmcontinue")
            if not continue_token:
                break

    def scrape_language_media(
        self,
        languages: list[str] | None = None,
        per_language: int = 25,
    ) -> dict[str, Any]:
        """
        Discover pronunciation media URLs, ping each link, keep only successes.
        Does not scrape article info.
        """
        languages = languages or list(LANGUAGE_CATEGORIES.keys())
        candidate_cap = max(per_language * 4, per_language)

        manifest: dict[str, Any] = {
            "source": "wikimedia_commons",
            "kind": "language_pronunciation_media",
            "scraped_info": False,
            "cdn_ping": self.cdn_ping,
            "languages": {},
            "summary": {"ok": 0, "failed": 0, "skipped": 0},
        }

        for lang in languages:
            category = LANGUAGE_CATEGORIES.get(lang)
            if not category:
                log(f"[{lang}] no category mapping; skipping")
                manifest["summary"]["skipped"] += 1
                continue

            log(
                f"[{lang}] collecting up to {per_language} verified media "
                f"from {category}"
            )
            verified: list[dict[str, Any]] = []
            failed: list[dict[str, Any]] = []
            tried = 0

            try:
                for item in self._iter_category_files(category):
                    if len(verified) >= per_language or tried >= candidate_cap:
                        break
                    tried += 1
                    log(f"[{lang}] ping {item['title']}")
                    result = self.ping_api(item["title"], item["url"])
                    record = {**item, "ping": result}
                    if result["ok"]:
                        verified.append(record)
                        manifest["summary"]["ok"] += 1
                        log(f"  OK ({len(verified)}/{per_language})")
                    else:
                        failed.append(record)
                        manifest["summary"]["failed"] += 1
                        log(f"  FAIL {result.get('error')}")
            except Exception as exc:
                log(f"[{lang}] category listing failed: {exc}")
                manifest["languages"][lang] = {
                    "category": category,
                    "verified": verified,
                    "failed": failed,
                    "error": str(exc),
                }
                continue

            lang_dir = self.language_dir / "wikipedia_media" / lang
            lang_dir.mkdir(parents=True, exist_ok=True)
            lang_manifest = {
                "language": lang,
                "category": category,
                "verified": verified,
                "failed": failed,
            }
            out_path = lang_dir / "manifest.json"
            out_path.write_text(
                json.dumps(lang_manifest, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
            log(
                f"[{lang}] wrote {out_path} "
                f"({len(verified)} ok / {len(failed)} failed)"
            )

            manifest["languages"][lang] = {
                "category": category,
                "manifest_path": str(out_path),
                "verified_count": len(verified),
                "failed_count": len(failed),
                "verified": verified,
                "failed": failed,
            }

        root_manifest = self.language_dir / "wikipedia_media" / "manifest.json"
        root_manifest.parent.mkdir(parents=True, exist_ok=True)
        root_manifest.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        log(
            f"Root manifest: {root_manifest} "
            f"(ok={manifest['summary']['ok']}, "
            f"failed={manifest['summary']['failed']})"
        )
        return manifest


if __name__ == "__main__":
    languages = ["en", "es", "fr", "de", "zh", "id"]
    per_language = 5
    cdn_ping = False

    args = [a for a in sys.argv[1:] if a != "--cdn-ping"]
    if "--cdn-ping" in sys.argv[1:]:
        cdn_ping = True
    if len(args) > 0:
        languages = args[0].split(",")
    if len(args) > 1:
        per_language = int(args[1])

    scraper = WikipediaMediaScraper(cdn_ping=cdn_ping)
    result = scraper.scrape_language_media(
        languages=languages, per_language=per_language
    )
    if result["summary"]["ok"] == 0:
        sys.exit(1)
