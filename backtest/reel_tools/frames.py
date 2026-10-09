"""
Save one frame every N seconds from a downloaded reel (PyAV decode, Pillow JPEG), so the chart, the
indicator settings and any on-screen text can be read as images. Frames go to the output folder as
f_<second>.jpg, downscaled to fit 540x960.

  pip install av Pillow
  python3 -I backtest/reel_tools/frames.py /path/to/scratch/reel_<id>/reel.mp4 /path/to/scratch/reel_<id>/frames [--every 3]
"""

import argparse
import os
import sys

import av


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("out_dir")
    ap.add_argument("--every", type=float, default=3.0, help="seconds between saved frames")
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    container = av.open(a.video)
    stream = container.streams.video[0]
    duration = float(stream.duration * stream.time_base) if stream.duration else None
    print("video duration", duration)
    saved, last = 0, -a.every
    for frame in container.decode(stream):
        t = float(frame.pts * stream.time_base)
        if t - last >= a.every:
            im = frame.to_image()
            im.thumbnail((540, 960))
            im.save(os.path.join(a.out_dir, f"f_{int(t):03d}.jpg"), quality=70)
            saved += 1
            last = t
    print("frames saved", saved)


if __name__ == "__main__":
    sys.exit(main())
