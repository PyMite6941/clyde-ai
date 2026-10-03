#!/usr/bin/env python3
"""
File processing pipeline: input -> process -> output.

Handles training JSONL, manifests, media sidecars, and plain text.
Writes structured artifacts under data/pipeline/{input,staging,output,logs}.
"""

from __future__ import annotations

import hashlib
import json
import mimetypes
import shutil
import sys
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable

AUDIO_SUFFIXES = {".wav", ".ogg", ".oga", ".opus", ".flac", ".mp3", ".webm"}
TEXT_SUFFIXES = {".txt", ".md", ".json", ".jsonl", ".csv", ".tsv", ".yaml", ".yml"}


def log(msg: str) -> None:
    print(msg, flush=True)


@dataclass
class PipelineRecord:
    source: str
    kind: str
    status: str
    output: str | None = None
    bytes_in: int = 0
    bytes_out: int = 0
    sha256: str | None = None
    error: str | None = None
    meta: dict[str, Any] = field(default_factory=dict)


class FileProcessingPipeline:
    """
    Stages:
      input/   - drop files here (or ingest from other data dirs)
      staging/ - normalized intermediate files
      output/  - final training-ready artifacts
      logs/    - run reports
    """

    def __init__(self, base_dir: str | Path = "data") -> None:
        self.base_dir = Path(base_dir)
        self.root = self.base_dir / "pipeline"
        self.input_dir = self.root / "input"
        self.staging_dir = self.root / "staging"
        self.output_dir = self.root / "output"
        self.logs_dir = self.root / "logs"
        for path in (
            self.input_dir,
            self.staging_dir,
            self.output_dir,
            self.logs_dir,
        ):
            path.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _sha256(path: Path, chunk: int = 1024 * 1024) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                block = handle.read(chunk)
                if not block:
                    break
                digest.update(block)
        return digest.hexdigest()

    @staticmethod
    def _detect_kind(path: Path) -> str:
        suffix = path.suffix.lower()
        if suffix in AUDIO_SUFFIXES:
            return "audio"
        if suffix == ".jsonl":
            return "jsonl"
        if suffix == ".json":
            return "json"
        if suffix in TEXT_SUFFIXES:
            return "text"
        guessed, _ = mimetypes.guess_type(str(path))
        if guessed and guessed.startswith("audio/"):
            return "audio"
        if guessed and guessed.startswith("text/"):
            return "text"
        return "binary"

    def _unique_dest(self, src_path: Path) -> Path:
        """Avoid collisions when multiple manifests share a filename."""
        dest = self.input_dir / src_path.name
        if not dest.exists():
            return dest
        # Prefer a parent-qualified name for clarity.
        qualified = self.input_dir / f"{src_path.parent.name}__{src_path.name}"
        if not qualified.exists() or qualified.resolve() == src_path.resolve():
            return qualified
        stem, suffix = src_path.stem, src_path.suffix
        idx = 2
        while True:
            candidate = self.input_dir / f"{stem}_{idx}{suffix}"
            if not candidate.exists():
                return candidate
            idx += 1

    def ingest(
        self,
        sources: Iterable[str | Path] | None = None,
        copy: bool = True,
    ) -> list[Path]:
        """
        Copy/link source files into pipeline/input.
        Always returns the full set of files present in input/ afterward.
        """
        if sources:
            for src in sources:
                src_path = Path(src)
                if not src_path.exists() or not src_path.is_file():
                    log(f"[pipeline] skip missing source: {src_path}")
                    continue
                dest = self._unique_dest(src_path)
                if dest.resolve() != src_path.resolve():
                    if copy:
                        shutil.copy2(src_path, dest)
                    else:
                        dest.write_bytes(src_path.read_bytes())
                log(f"[pipeline] ingested {dest.name}")
        return sorted(p for p in self.input_dir.iterdir() if p.is_file())

    def _normalize_jsonl(self, path: Path, staging: Path) -> PipelineRecord:
        records_out = 0
        bytes_in = path.stat().st_size
        with path.open("r", encoding="utf-8") as src, staging.open(
            "w", encoding="utf-8"
        ) as dst:
            for line_no, line in enumerate(src, start=1):
                raw = line.strip()
                if not raw:
                    continue
                try:
                    obj = json.loads(raw)
                except json.JSONDecodeError as exc:
                    return PipelineRecord(
                        source=str(path),
                        kind="jsonl",
                        status="error",
                        error=f"line {line_no}: {exc}",
                        bytes_in=bytes_in,
                    )
                # ensure stable training shape
                if "messages" in obj and "tools" not in obj:
                    obj["tools"] = obj.get("tools") or []
                if "id" not in obj:
                    obj["id"] = f"{path.stem}_{line_no}"
                dst.write(json.dumps(obj, ensure_ascii=False) + "\n")
                records_out += 1
        return PipelineRecord(
            source=str(path),
            kind="jsonl",
            status="ok",
            output=str(staging),
            bytes_in=bytes_in,
            bytes_out=staging.stat().st_size,
            sha256=self._sha256(staging),
            meta={"records": records_out},
        )

    def _normalize_json(self, path: Path, staging: Path) -> PipelineRecord:
        bytes_in = path.stat().st_size
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            return PipelineRecord(
                source=str(path),
                kind="json",
                status="error",
                error=str(exc),
                bytes_in=bytes_in,
            )
        staging.write_text(
            json.dumps(data, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        return PipelineRecord(
            source=str(path),
            kind="json",
            status="ok",
            output=str(staging),
            bytes_in=bytes_in,
            bytes_out=staging.stat().st_size,
            sha256=self._sha256(staging),
        )

    def _normalize_text(self, path: Path, staging: Path) -> PipelineRecord:
        bytes_in = path.stat().st_size
        text = path.read_text(encoding="utf-8", errors="replace")
        normalized = "\n".join(line.rstrip() for line in text.splitlines()).strip() + "\n"
        staging.write_text(normalized, encoding="utf-8")
        return PipelineRecord(
            source=str(path),
            kind="text",
            status="ok",
            output=str(staging),
            bytes_in=bytes_in,
            bytes_out=staging.stat().st_size,
            sha256=self._sha256(staging),
            meta={"chars": len(normalized)},
        )

    def _normalize_audio(self, path: Path, staging: Path) -> PipelineRecord:
        """Pass-through audio with sidecar metadata JSON (no re-encode)."""
        bytes_in = path.stat().st_size
        shutil.copy2(path, staging)
        sidecar = staging.with_suffix(staging.suffix + ".meta.json")
        meta = {
            "filename": path.name,
            "bytes": bytes_in,
            "sha256": self._sha256(path),
            "kind": "audio",
            "suffix": path.suffix.lower(),
        }
        sidecar.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return PipelineRecord(
            source=str(path),
            kind="audio",
            status="ok",
            output=str(staging),
            bytes_in=bytes_in,
            bytes_out=staging.stat().st_size,
            sha256=meta["sha256"],
            meta={"sidecar": str(sidecar)},
        )

    def _normalize_binary(self, path: Path, staging: Path) -> PipelineRecord:
        bytes_in = path.stat().st_size
        shutil.copy2(path, staging)
        return PipelineRecord(
            source=str(path),
            kind="binary",
            status="ok",
            output=str(staging),
            bytes_in=bytes_in,
            bytes_out=staging.stat().st_size,
            sha256=self._sha256(staging),
        )

    def process_file(self, path: Path, operation: str = "normalize") -> PipelineRecord:
        kind = self._detect_kind(path)
        staging = self.staging_dir / f"{path.stem}.staging{path.suffix}"

        handlers: dict[str, Callable[[Path, Path], PipelineRecord]] = {
            "jsonl": self._normalize_jsonl,
            "json": self._normalize_json,
            "text": self._normalize_text,
            "audio": self._normalize_audio,
            "binary": self._normalize_binary,
        }

        if operation == "validate":
            # validate-only: normalize to staging then keep status
            record = handlers[kind](path, staging)
            if record.status == "ok":
                record.meta["validated"] = True
            return record

        if operation not in ("normalize", "to_jsonl", "manifest", "validate"):
            return PipelineRecord(
                source=str(path),
                kind=kind,
                status="error",
                error=f"unknown operation: {operation}",
            )

        record = handlers[kind](path, staging)
        if record.status != "ok" or not record.output:
            return record

        # Promote staging -> output
        out_name = path.name
        if operation == "to_jsonl" and kind != "jsonl":
            out_name = f"{path.stem}.jsonl"
            out_path = self.output_dir / out_name
            if kind == "json":
                data = json.loads(Path(record.output).read_text(encoding="utf-8"))
                rows = data if isinstance(data, list) else [data]
                with out_path.open("w", encoding="utf-8") as handle:
                    for row in rows:
                        handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            else:
                payload = {
                    "id": path.stem,
                    "source": str(path),
                    "kind": kind,
                    "text": Path(record.output).read_text(encoding="utf-8", errors="replace")
                    if kind == "text"
                    else None,
                    "sha256": record.sha256,
                }
                out_path.write_text(
                    json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8"
                )
            record.output = str(out_path)
            record.bytes_out = out_path.stat().st_size
            record.meta["operation"] = operation
            return record

        out_path = self.output_dir / out_name
        shutil.copy2(record.output, out_path)
        record.output = str(out_path)
        record.bytes_out = out_path.stat().st_size
        record.meta["operation"] = operation
        return record

    def run(
        self,
        sources: Iterable[str | Path] | None = None,
        operation: str = "normalize",
        ingest_defaults: bool = True,
    ) -> dict[str, Any]:
        """
        Full pipeline run.
        If ingest_defaults, also pull tools training JSONL and language media
        manifests into input for processing.
        """
        started = time.time()
        auto_sources: list[Path] = []
        if ingest_defaults:
            candidates = [
                self.base_dir / "tools" / "training" / "tool_use_train.jsonl",
                self.base_dir / "tools" / "training" / "manifest.json",
                self.base_dir / "language" / "wikipedia_media" / "manifest.json",
            ]
            # sample a few audio files if present
            media_root = self.base_dir / "language" / "wikipedia_media"
            if media_root.exists():
                for audio in media_root.glob("*/files/*"):
                    if audio.is_file() and audio.suffix.lower() in AUDIO_SUFFIXES:
                        auto_sources.append(audio)
                        if len(auto_sources) >= 3:
                            break
            auto_sources.extend(p for p in candidates if p.exists())

        combined: list[str | Path] = []
        if sources:
            combined.extend(sources)
        combined.extend(auto_sources)

        inputs = self.ingest(combined if combined else None)
        records: list[PipelineRecord] = []
        for path in inputs:
            log(f"[pipeline] {operation} {path.name}")
            record = self.process_file(path, operation=operation)
            records.append(record)
            if record.status == "ok":
                log(f"  OK -> {record.output}")
            else:
                log(f"  FAIL {record.error}")

        # Write combined training pack from successful jsonl outputs
        pack_path = self.output_dir / "training_pack.jsonl"
        packed = 0
        with pack_path.open("w", encoding="utf-8") as pack:
            for record in records:
                if record.status != "ok" or not record.output:
                    continue
                out = Path(record.output)
                if out.suffix.lower() != ".jsonl":
                    continue
                for line in out.read_text(encoding="utf-8").splitlines():
                    if line.strip():
                        pack.write(line.rstrip() + "\n")
                        packed += 1

        report = {
            "kind": "file_processing_pipeline",
            "operation": operation,
            "started_unix": started,
            "elapsed_sec": round(time.time() - started, 3),
            "input_dir": str(self.input_dir),
            "staging_dir": str(self.staging_dir),
            "output_dir": str(self.output_dir),
            "inputs": len(inputs),
            "ok": sum(1 for r in records if r.status == "ok"),
            "failed": sum(1 for r in records if r.status != "ok"),
            "training_pack": str(pack_path),
            "training_pack_records": packed,
            "records": [asdict(r) for r in records],
        }
        stamp = time.strftime("%Y%m%d_%H%M%S")
        report_path = self.logs_dir / f"run_{stamp}.json"
        latest_path = self.logs_dir / "latest.json"
        payload = json.dumps(report, indent=2, ensure_ascii=False)
        report_path.write_text(payload, encoding="utf-8")
        latest_path.write_text(payload, encoding="utf-8")
        # also emit a machine-readable manifest in output/
        (self.output_dir / "pipeline_manifest.json").write_text(payload, encoding="utf-8")
        log(
            f"[pipeline] done ok={report['ok']} failed={report['failed']} "
            f"pack_records={packed} report={report_path}"
        )
        return report

    def seed_sample_input(self) -> Path:
        """Write a tiny sample JSONL into input/ for smoke tests."""
        sample = self.input_dir / "sample_tools.jsonl"
        rows = [
            {
                "id": "sample_1",
                "category": "mcp",
                "messages": [
                    {"role": "user", "content": "List MCP tools on server demo."},
                    {
                        "role": "assistant",
                        "content": "Listing tools.",
                        "tool_calls": [
                            {
                                "id": "c1",
                                "type": "function",
                                "function": {
                                    "name": "mcp_list_tools",
                                    "arguments": "{\"server\":\"demo\"}",
                                },
                            }
                        ],
                    },
                ],
            }
        ]
        with sample.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        return sample


if __name__ == "__main__":
    operation = "normalize"
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    for a in sys.argv[1:]:
        if a.startswith("--op="):
            operation = a.split("=", 1)[1]

    pipeline = FileProcessingPipeline()
    if "--seed" in sys.argv:
        path = pipeline.seed_sample_input()
        log(f"[pipeline] seeded {path}")

    sources = args or None
    report = pipeline.run(sources=sources, operation=operation, ingest_defaults=True)
    if report["failed"] > 0 and report["ok"] == 0:
        sys.exit(1)
