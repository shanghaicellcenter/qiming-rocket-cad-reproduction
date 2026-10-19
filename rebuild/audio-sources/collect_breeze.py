#!/usr/bin/env python3
"""Collect existing Breeze2 candidates; this script never requests generation.

Examples:
    python3 collect_breeze.py
    python3 collect_breeze.py --remote spark --destination ./collected
    python3 collect_breeze.py --verify-only --destination ./collected

Only the fixed remote directory below and canonical results/ paths are read.
ASR and sentence alignment files are evidence attachments, never approval.
The candidate manifest always keeps eligible_for_final_movie false.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import shlex
import subprocess
import sys
import tempfile
import wave


REMOTE_ROOT = "/home/qianqiming/codex-qiming-assembly-breeze-20261019"
STATUS_REL = "results/status.json"
MANIFEST_NAME = "breeze-candidate-manifest.json"
ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,127}\Z")
SHA_RE = re.compile(r"[0-9a-fA-F]{64}\Z")
REMOTE_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.@-]{0,253}\Z")
DURATION_TOLERANCE = 0.000001


class CollectionError(Exception):
    """An input, transfer, or media check failed."""


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def checked_sha(value: object, field: str) -> str:
    if not isinstance(value, str) or not SHA_RE.fullmatch(value):
        raise CollectionError(f"{field}: expected a SHA256 hexadecimal string")
    return value.lower()


def checked_id(value: object) -> str:
    if not isinstance(value, str) or not ID_RE.fullmatch(value):
        raise CollectionError("clip id must contain only ASCII letters, digits, _ or -")
    return value


def results_path(value: object) -> PurePosixPath:
    if not isinstance(value, str) or "\\" in value:
        raise CollectionError("remote file path must be a results/ relative path")
    path = PurePosixPath(value)
    if (
        path.is_absolute()
        or len(path.parts) < 2
        or path.parts[0] != "results"
        or any(part in (".", "..") for part in path.parts)
        or str(path) != value
        or any(ord(char) < 32 or ord(char) == 127 for char in value)
    ):
        raise CollectionError(f"disallowed results path: {value!r}")
    return path


def local_path(destination: Path, relative: str) -> Path:
    parts = results_path(relative).parts
    current = destination
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise CollectionError(f"local symlinks are not permitted: {current}")
    if not current.resolve().is_relative_to(destination):
        raise CollectionError("local file would escape the collection directory")
    return current


def read_json(path: Path) -> object:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise CollectionError(f"cannot read JSON {path}: {error}") from error


def load_status(path: Path) -> tuple[dict, list[dict]]:
    status = read_json(path)
    if not isinstance(status, dict) or status.get("engine") != "Breeze2":
        raise CollectionError("status.json must declare engine exactly 'Breeze2'")
    checked_sha(status.get("source_narration_sha256"), "source_narration_sha256")
    checked_sha(status.get("reference_sha256"), "reference_sha256")
    if not isinstance(status.get("clips"), list):
        raise CollectionError("status.json clips must be an array")

    candidates = []
    seen = set()
    for clip in status["clips"]:
        if not isinstance(clip, dict):
            raise CollectionError("every clip record must be an object")
        clip_id = checked_id(clip.get("id"))
        if clip_id in seen:
            raise CollectionError(f"duplicate clip id: {clip_id}")
        seen.add(clip_id)
        if clip.get("status") != "generated_candidate":
            continue
        text = clip.get("text")
        if not isinstance(text, str) or not text.strip():
            raise CollectionError(f"{clip_id}: candidate text must be nonempty")
        text_hash = checked_sha(clip.get("text_sha256"), f"{clip_id}.text_sha256")
        if hashlib.sha256(text.encode("utf-8")).hexdigest() != text_hash:
            raise CollectionError(f"{clip_id}: text SHA256 mismatch")
        expected_wav = f"results/{clip_id}/{clip_id}.wav"
        results_path(clip.get("wav_file"))
        if clip["wav_file"] != expected_wav:
            raise CollectionError(f"{clip_id}: wav_file must be {expected_wav}")
        checked_sha(clip.get("wav_sha256"), f"{clip_id}.wav_sha256")
        for field, expected in (("sample_rate", 24000), ("channels", 1), ("sample_width", 2)):
            if type(clip.get(field)) is not int or clip[field] != expected:
                raise CollectionError(f"{clip_id}: {field} must equal {expected}")
        frames = clip.get("frames")
        duration = clip.get("duration_seconds")
        if type(frames) is not int or frames <= 0:
            raise CollectionError(f"{clip_id}: frames must be a positive integer")
        if (
            type(duration) not in (int, float)
            or not math.isfinite(duration)
            or duration <= 0
            or abs(duration - frames / 24000) > DURATION_TOLERANCE
        ):
            raise CollectionError(f"{clip_id}: duration does not match frames / 24000")
        candidates.append(clip)
    return status, candidates


class RemoteReader:
    def __init__(self, remote: str):
        if not REMOTE_RE.fullmatch(remote) or remote.count("@") > 1:
            raise CollectionError("--remote must be a plain SSH host alias or user@host")
        self.remote = remote

    def fetch(self, relative: str, target: Path, *, optional: bool = False) -> bool:
        # Paths are validated locally, then checked remotely to reject symlink escapes.
        remote_file = f"{REMOTE_ROOT}/{results_path(relative)}"
        quoted = shlex.quote(remote_file)
        check = (
            f"if [ ! -e {quoted} ]; then exit 44; fi; "
            f"[ -f {quoted} ] || exit 45; "
            f"resolved=$(readlink -f -- {quoted}) || exit 46; "
            f"[ \"$resolved\" = {quoted} ] || exit 47"
        )
        try:
            result = subprocess.run(
                ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "--", self.remote, check],
                capture_output=True, text=True, timeout=30, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CollectionError(f"SSH read check failed for {relative}: {error}") from error
        if result.returncode == 44 and optional:
            return False
        if result.returncode != 0:
            detail = result.stderr.strip() or f"remote check exit {result.returncode}"
            raise CollectionError(f"cannot read fixed remote file {relative}: {detail}")

        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(prefix=".collect-", dir=target.parent, delete=False) as staging:
                temporary = Path(staging.name)
            transfer = subprocess.run(
                ["scp", "-q", "-o", "BatchMode=yes", "-o", "ConnectTimeout=10", "--",
                 f"{self.remote}:{remote_file}", str(temporary)],
                capture_output=True, text=True, timeout=120, check=False,
            )
            if transfer.returncode != 0:
                detail = transfer.stderr.strip() or f"scp exit {transfer.returncode}"
                raise CollectionError(f"copy failed for {relative}: {detail}")
            os.replace(temporary, target)
            temporary = None
        except (OSError, subprocess.TimeoutExpired) as error:
            raise CollectionError(f"copy failed for {relative}: {error}") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        return True


def verify_wav(path: Path, clip: dict) -> dict:
    clip_id = clip["id"]
    actual_hash = sha256_file(path)
    if actual_hash != checked_sha(clip["wav_sha256"], f"{clip_id}.wav_sha256"):
        raise CollectionError(f"{clip_id}: WAV SHA256 mismatch")
    try:
        with wave.open(str(path), "rb") as audio:
            rate, channels, width, frames = (
                audio.getframerate(), audio.getnchannels(), audio.getsampwidth(), audio.getnframes()
            )
            if (rate, channels, width, audio.getcomptype()) != (24000, 1, 2, "NONE"):
                raise CollectionError(f"{clip_id}: WAV must be uncompressed 24000 Hz mono 16-bit PCM")
            decoded_bytes = 0
            while chunk := audio.readframes(65536):
                decoded_bytes += len(chunk)
            if decoded_bytes != frames * channels * width:
                raise CollectionError(f"{clip_id}: truncated or inconsistent PCM frame payload")
    except (OSError, EOFError, wave.Error) as error:
        raise CollectionError(f"{clip_id}: invalid WAV: {error}") from error
    duration = frames / rate
    if frames != clip["frames"] or abs(duration - clip["duration_seconds"]) > DURATION_TOLERANCE:
        raise CollectionError(f"{clip_id}: actual WAV frames or duration differs from status.json")
    return {
        "wav_sha256": actual_hash, "sample_rate": rate, "channels": channels,
        "sample_width": width, "frames": frames, "duration_seconds": duration,
    }


def build_manifest(destination: Path, status: dict, candidates: list[dict], reader: RemoteReader | None,
                   existing_manifest: dict | None = None) -> dict:
    # In verify-only mode, verify the saved snapshot's attachments. Unreferenced
    # sidecars from a previous collection are retained, but are not new evidence.
    saved_clips = {}
    if existing_manifest is not None:
        if (
            not isinstance(existing_manifest, dict)
            or existing_manifest.get("engine") != "Breeze2"
            or existing_manifest.get("eligible_for_final_movie") is not False
            or not isinstance(existing_manifest.get("clips"), list)
        ):
            raise CollectionError("existing candidate manifest is not an ineligible Breeze2 manifest")
        for saved in existing_manifest["clips"]:
            if not isinstance(saved, dict) or saved.get("eligible_for_final_movie") is not False:
                raise CollectionError("every saved candidate must explicitly remain ineligible")
            saved_id = checked_id(saved.get("id"))
            if saved_id in saved_clips:
                raise CollectionError("duplicate id in existing candidate manifest")
            saved_clips[saved_id] = saved
    clips = []
    for clip in candidates:
        clip_id = clip["id"]
        wav_path = local_path(destination, clip["wav_file"])
        if reader is not None:
            reader.fetch(clip["wav_file"], wav_path)
        media = verify_wav(wav_path, clip)
        record = {
            "id": clip_id, "status": "generated_candidate", "text": clip["text"],
            "text_sha256": checked_sha(clip["text_sha256"], f"{clip_id}.text_sha256"),
            "wav_file": clip["wav_file"], **media,
            "asr_file": None, "asr_sha256": None,
            "sentence_alignment_file": None, "sentence_alignment_sha256": None,
            "eligible_for_final_movie": False,
        }
        for suffix, path_key, hash_key in (
            ("asr.json", "asr_file", "asr_sha256"),
            ("sentence-alignment.json", "sentence_alignment_file", "sentence_alignment_sha256"),
        ):
            relative = f"results/{clip_id}/{clip_id}.{suffix}"
            attachment = local_path(destination, relative)
            if reader is not None:
                present = reader.fetch(relative, attachment, optional=True)
            elif existing_manifest is not None:
                saved_value = saved_clips.get(clip_id, {}).get(path_key)
                if saved_value not in (None, relative):
                    raise CollectionError(f"{clip_id}: disallowed saved attachment path")
                present = saved_value is not None
            else:
                present = attachment.is_file()
            if present:
                read_json(attachment)  # Check syntax only; it cannot grant approval.
                record[path_key] = relative
                record[hash_key] = sha256_file(attachment)
        clips.append(record)
    return {
        "engine": "Breeze2",
        "source_narration_sha256": checked_sha(status["source_narration_sha256"], "source_narration_sha256"),
        "reference_sha256": checked_sha(status["reference_sha256"], "reference_sha256"),
        "source_status_file": STATUS_REL,
        "source_status_sha256": sha256_file(local_path(destination, STATUS_REL)),
        "remote_root": REMOTE_ROOT,
        "eligible_for_final_movie": False,
        "clips": clips,
    }


def write_manifest(path: Path, manifest: dict) -> None:
    if path.is_symlink():
        raise CollectionError("candidate manifest must not be a symlink")
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", prefix=".manifest-",
                                         dir=path.parent, delete=False) as staging:
            temporary = Path(staging.name)
            json.dump(manifest, staging, ensure_ascii=False, indent=2, allow_nan=False)
            staging.write("\n")
        os.replace(temporary, path)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--remote", default="spark", help="SSH host alias (default: spark)")
    parser.add_argument("--destination", type=Path, default=Path(__file__).resolve().parent / "collected")
    parser.add_argument("--verify-only", action="store_true", help="read and verify local files only; never run SSH/scp")
    args = parser.parse_args(argv)
    destination = args.destination.expanduser().resolve()
    try:
        if args.verify_only:
            if not destination.is_dir():
                raise CollectionError(f"collection directory does not exist: {destination}")
            reader = None
        else:
            reader = RemoteReader(args.remote)
            destination.mkdir(parents=True, exist_ok=True)
        status_path = local_path(destination, STATUS_REL)
        if reader is not None:
            reader.fetch(STATUS_REL, status_path)
        status, candidates = load_status(status_path)
        manifest_path = destination / MANIFEST_NAME
        existing_manifest = None
        if args.verify_only:
            if manifest_path.is_symlink():
                raise CollectionError("candidate manifest must not be a symlink")
            if manifest_path.exists():
                existing_manifest = read_json(manifest_path)
        manifest = build_manifest(destination, status, candidates, reader, existing_manifest)
        if args.verify_only:
            if existing_manifest is not None and existing_manifest != manifest:
                raise CollectionError("existing candidate manifest differs from verified local evidence")
        else:
            write_manifest(manifest_path, manifest)
        print(json.dumps({
            "mode": "verify_only" if args.verify_only else "collect",
            "engine": "Breeze2", "verified_candidate_count": len(manifest["clips"]),
            "eligible_for_final_movie": False, "destination": str(destination),
            "candidate_manifest": str(manifest_path) if manifest_path.exists() else None,
        }, ensure_ascii=False, indent=2))
        return 0
    except (CollectionError, OSError) as error:
        print(f"Breeze2 collection failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
