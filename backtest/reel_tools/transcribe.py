"""
Transcribe a downloaded reel's audio track with faster-whisper (CPU, int8), one line per segment:
`[start-end] text`. Used to read Instagram strategy reels before mechanizing them (see README.md here).

Print to the terminal or redirect into the reel's own scratch folder. Raw transcripts are NOT
committed to the repository (standing rule from the user); quote only the few lines a DEVLOG entry needs.

  pip install faster-whisper
  python3 -I backtest/reel_tools/transcribe.py /path/to/scratch/reel_<id>/reel.mp4 [--model small]
"""

import argparse
import sys

from faster_whisper import WhisperModel


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("media", help="video or audio file (anything ffmpeg/PyAV can decode)")
    ap.add_argument("--model", default="small", help="whisper model size: tiny, base, small, medium")
    ap.add_argument("--language", default=None, help="force a language code, e.g. en (default: detect)")
    a = ap.parse_args()
    model = WhisperModel(a.model, device="cpu", compute_type="int8")
    segments, info = model.transcribe(a.media, beam_size=5, language=a.language)
    print(f"[language {info.language}, duration {info.duration:.0f}s]")
    for s in segments:
        print(f"[{s.start:5.1f}-{s.end:5.1f}] {s.text.strip()}")


if __name__ == "__main__":
    sys.exit(main())
