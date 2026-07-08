"""Regenerate ONLY the missing Seedance clips for 《上岸先斩意中人》.

Previously 4/7 succeeded (clip_01/03/04/05). clip_02/06/07 failed because the
Volcengine account hit the inference limit on doubao-seedance-1-5-pro
('Safe Experience Mode' paused). This script only retries the missing ones so
we never re-spend on the 4 clips that already landed.

Reuses CLIPS / generate() from gen_clips.py (safe: gen_clips.main is guarded).
After generation it auto-invokes compose.py to build the final 60s film.
"""
from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

# import gen_clips as a module (does NOT run main(), guarded by __main__)
spec = importlib.util.spec_from_file_location("gen_clips", ROOT / "gen_clips.py")
gc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gc)

OUT = gc.OUT  # output dir from gen_clips


def missing_clips():
    """Clips whose .mp4 hasn't landed yet."""
    have = {p.stem for p in OUT.glob("clip_*.mp4")}
    return [c for c in gc.CLIPS if c["name"] not in have]


def main():
    targets = missing_clips()
    if not targets:
        print("NOTHING_MISSING -> compose")
        subprocess.run([sys.executable, str(ROOT / "compose.py")], check=False)
        return
    print(f"Regenerating {len(targets)} missing clips: {[t['name'] for t in targets]}")
    results = gc.run_missing(targets)  # type: ignore[attr-defined]
    ok = sum(1 for v in results.values() if v == "ok")
    print(f"MISSING_GEN_DONE ok={ok}/{len(targets)}")
    if ok == len(targets):
        print("=== COMPOSE ===")
        subprocess.run([sys.executable, str(ROOT / "compose.py")], check=False)
        ff = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
        out = ROOT / "projects" / "shang-an-xian-zhan-yi-zhong-ren" / "renders" / "final.mp4"
        if out.exists():
            subprocess.run(
                [ff, "-v", "error", "-show_entries",
                 "format=duration:stream=codec_name,width,height",
                 "-of", "default=noprint_wrappers=1", str(out)],
                check=False,
            )
            print("VERIFY_DONE")
    else:
        still = [n for n, v in results.items() if v != "ok"]
        print(f"STILL_LIMITED ({still}): visit Volcengine Model Activation page to "
              f"lift 'Safe Experience Mode' or wait for the daily quota to reset, "
              f"then re-run: python gen_missing.py")


if __name__ == "__main__":
    main()
