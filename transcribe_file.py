#!/usr/bin/env python3
"""
transcribe_file.py

Batch-transcribe (and optionally translate) a video or audio file using MLX Whisper.
Outputs SRT, VTT, or plain text. No Ollama required.

Usage:
    # Translate Ukrainian (or any language) to English — best quality model:
    python transcribe_file.py video.mp4 --task translate --whisper large

    # Transcribe only, keep original language:
    python transcribe_file.py recording.wav --task transcribe --whisper large

    # Fast pass with turbo model:
    python transcribe_file.py clip.mp4 --whisper turbo --task translate

    # Save as SRT:
    python transcribe_file.py video.mp4 --task translate --format srt -o subtitles.srt
"""

import argparse
import sys
from pathlib import Path

WHISPER_MODELS = {
    "small": "mlx-community/whisper-small-mlx",
    "medium": "mlx-community/whisper-medium-mlx",
    "turbo": "mlx-community/whisper-large-v3-turbo",
    "large": "mlx-community/whisper-large-v3-mlx",
}

# Approx VRAM: small ~150MB, medium ~500MB, turbo ~1.5GB, large ~3GB
WHISPER_SIZE_INFO = {
    "small": "~150MB",
    "medium": "~500MB",
    "turbo": "~1.5GB",
    "large": "~3GB",
}


def format_timestamp(seconds: float, vtt: bool = False) -> str:
    ms = int(round(seconds * 1000))
    h = ms // 3_600_000
    ms %= 3_600_000
    m = ms // 60_000
    ms %= 60_000
    s = ms // 1_000
    ms %= 1_000
    sep = "." if vtt else ","
    return f"{h:02d}:{m:02d}:{s:02d}{sep}{ms:03d}"


def to_srt(segments) -> str:
    lines = []
    for i, seg in enumerate(segments, 1):
        start = format_timestamp(seg["start"])
        end = format_timestamp(seg["end"])
        text = seg["text"].strip()
        lines.append(f"{i}\n{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def to_vtt(segments) -> str:
    lines = ["WEBVTT", ""]
    for seg in segments:
        start = format_timestamp(seg["start"], vtt=True)
        end = format_timestamp(seg["end"], vtt=True)
        text = seg["text"].strip()
        lines.append(f"{start} --> {end}\n{text}\n")
    return "\n".join(lines)


def to_txt(segments) -> str:
    return "\n".join(seg["text"].strip() for seg in segments if seg["text"].strip())


def main():
    p = argparse.ArgumentParser(
        description="Batch transcribe/translate a video or audio file with MLX Whisper."
    )
    p.add_argument("input", help="Path to video or audio file")
    p.add_argument(
        "--whisper",
        choices=WHISPER_MODELS.keys(),
        default="large",
        help="Whisper model size (default: large ~3GB for best quality)",
    )
    p.add_argument(
        "--task",
        choices=["transcribe", "translate"],
        default="translate",
        help="'translate' outputs English from any source; 'transcribe' keeps original language (default: translate)",
    )
    p.add_argument(
        "--source",
        default=None,
        help="Source language hint, e.g. 'uk' for Ukrainian (default: auto-detect)",
    )
    p.add_argument(
        "--format",
        choices=["srt", "vtt", "txt"],
        default="srt",
        help="Output format (default: srt)",
    )
    p.add_argument(
        "-o", "--output",
        default=None,
        help="Output file path (default: input filename with new extension)",
    )
    args = p.parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        sys.exit(f"File not found: {input_path}")

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.with_suffix(f".{args.format}")

    model_repo = WHISPER_MODELS[args.whisper]
    size_info = WHISPER_SIZE_INFO[args.whisper]
    print(f"Model: {args.whisper} ({size_info})  repo: {model_repo}")
    print(f"Task:  {args.task}  source: {args.source or 'auto'}")
    print(f"Input: {input_path}")
    print(f"Output: {output_path} ({args.format.upper()})")
    print("Transcribing... (this may take a minute for large files)")

    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(input_path),
        path_or_hf_repo=model_repo,
        task=args.task,
        language=args.source,
        word_timestamps=False,
        verbose=False,
    )

    segments = result.get("segments", [])
    detected = result.get("language", "unknown")
    print(f"Detected source language: {detected}  |  {len(segments)} segments")

    if args.format == "srt":
        content = to_srt(segments)
    elif args.format == "vtt":
        content = to_vtt(segments)
    else:
        content = to_txt(segments)

    output_path.write_text(content, encoding="utf-8")
    print(f"Saved: {output_path}")


if __name__ == "__main__":
    main()
