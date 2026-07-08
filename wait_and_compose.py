"""Wait for the background gen_clips.py to finish writing all 7 clips,
then compose + verify. Pure-python poll loop (no cmd label tricks).
"""
from __future__ import annotations
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJ = ROOT / "projects" / "shang-an-xian-zhan-yi-zhong-ren"
OUT = PROJ / "assets" / "video"
REND = PROJ / "renders"
FF = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"

clips = [OUT / f"clip_{i:02d}.mp4" for i in range(1, 8)]


def present() -> list[Path]:
    return [c for c in clips if c.exists() and c.stat().st_size > 10000]


def main():
    deadline = time.time() + 600
    while time.time() < deadline:
        have = present()
        if len(have) == len(clips):
            print(f"ALL_CLIPS_PRESENT ({len(have)}/7)")
            break
        miss = [c.name for c in clips if c not in have]
        print(f"waiting... have={len(have)}/7 missing={miss}", flush=True)
        time.sleep(15)
    else:
        print("TIMEOUT_WAITING_CLIPS", flush=True)
        sys.exit(1)

    # compose
    print("=== COMPOSE ===", flush=True)
    r = subprocess.run(
        [sys.executable, "compose.py"],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print("COMPOSE rc=", r.returncode, flush=True)
    print((r.stderr or "")[-2500:], flush=True)
    if r.returncode != 0:
        sys.exit(1)

    # verify
    final = REND / "final.mp4"
    print("=== VERIFY ===", flush=True)
    v = subprocess.run(
        [FF, "-v", "error",
         "-show_entries", "format=duration:stream=codec_name,width,height,pix_fmt,r_frame_rate,nb_frames",
         "-of", "default=noprint_wrappers=1", str(final)],
        capture_output=True, text=True, encoding="utf-8", errors="replace",
    )
    print(v.stdout, flush=True)
    print("VERIFY_rc=", v.returncode, flush=True)
    print("PIPELINE_DONE", flush=True)


if __name__ == "__main__":
    main()
