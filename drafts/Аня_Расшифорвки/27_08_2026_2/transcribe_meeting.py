#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Rasshifrovka audio sobraniya 27.08.2026_2 (faster-whisper)."""

import sys
from pathlib import Path

from faster_whisper import WhisperModel

OUT_DIR = Path(r"c:\1c\Cursor_1c\WIM_DEV\drafts\Аня_Расшифорвки\27_08_2026_2")
AUDIO_EXTS = {".m4a", ".mp3", ".wav", ".mp4", ".aac", ".ogg", ".wma", ".flac"}
TXT = OUT_DIR / "transcript.txt"
SRT = OUT_DIR / "transcript.srt"
MD = OUT_DIR / "transcript.md"


def find_audio() -> Path | None:
    files = [
        p for p in OUT_DIR.iterdir()
        if p.is_file() and p.suffix.lower() in AUDIO_EXTS
    ]
    if not files:
        return None
    files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return files[0]


def fmt_ts(seconds: float) -> str:
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    ms = int((seconds - int(seconds)) * 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def log(msg: str) -> None:
    print(msg, flush=True)


def main() -> int:
    audio = find_audio()
    if audio is None:
        log(f"ERROR: no audio in {OUT_DIR}")
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    log("Loading model small (int8, cpu)...")
    model = WhisperModel("small", device="cpu", compute_type="int8")
    log("Model loaded.")

    log(f"Transcribing: {audio.name}")
    segments, info = model.transcribe(
        str(audio),
        language="ru",
        vad_filter=True,
        beam_size=5,
    )

    log(f"Detected language: {info.language}, duration: {info.duration:.1f}s")

    lines = []
    srt_parts = []
    md_parts = [
        "# Rasshifrovka sobraniya",
        "",
        f"- Fail: `{audio.name}`",
        f"- Yazyk: {info.language}",
        f"- Dlitel'nost': {info.duration:.1f} sek",
        "",
        "## Tekst",
        "",
    ]

    plain_parts = []
    for i, seg in enumerate(segments, start=1):
        start = seg.start
        end = seg.end
        text = (seg.text or "").strip()
        if not text:
            continue
        stamp = f"[{fmt_ts(start)[:-4]} - {fmt_ts(end)[:-4]}]"
        line = f"{stamp} {text}"
        lines.append(line)
        plain_parts.append(text)
        md_parts.append(f"**{stamp}** {text}")
        md_parts.append("")
        srt_parts.append(str(i))
        srt_parts.append(f"{fmt_ts(start)} --> {fmt_ts(end)}")
        srt_parts.append(text)
        srt_parts.append("")
        if i % 10 == 0:
            log(f"  segments: {i}, last={fmt_ts(end)[:-4]}")

    TXT.write_text(
        "\n".join(lines) + "\n\n--- FULL TEXT ---\n\n" + " ".join(plain_parts) + "\n",
        encoding="utf-8",
    )
    SRT.write_text("\n".join(srt_parts), encoding="utf-8")
    MD.write_text("\n".join(md_parts) + "\n", encoding="utf-8")

    log(f"OK: wrote {TXT}")
    log(f"OK: wrote {SRT}")
    log(f"OK: wrote {MD}")
    log(f"Segments: {len(lines)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
