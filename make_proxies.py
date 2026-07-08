"""Build FREE 'proxy beats' for the 2 missing Seedance clips (clip_02 系绳,
clip_06 荣归) using ONLY the already-generated real footage.

Approach (Plan A): extract a key still from an existing real clip, apply a
slow Ken Burns zoom (ffmpeg zoompan) + a silent audio track, and emit a short
mp4 named clip_0X_proxy.mp4. compose.py prefers clip_0X.mp4 and falls back to
clip_0X_proxy.mp4, so when the user later restores Volcengine quota and runs
gen_missing.py, the REAL clips regenerate and overwrite automatically.

No API, no download, 100% real Seedance frames -> visual continuity preserved.
"""
from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
VID = ROOT / "projects" / "shang-an-xian-zhan-yi-zhong-ren" / "assets" / "video"
FF = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"


def run(args):
    r = subprocess.run([FF, "-y", *args], capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("FFMPEG FAIL:", r.stderr[-1500:])
        raise SystemExit(1)
    return r


def extract_frame(src: Path, t: float, out: Path):
    run(["-ss", f"{t}", "-i", str(src), "-frames:v", "1", str(out)])


def zoomclip(img: Path, dur: float, out: Path, zoom_end: float = 1.06):
    frames = int(dur * 24)
    zexpr = f"1.0+({zoom_end}-1.0)*(on/{frames})"
    vf = (f"scale=1280:720,zoompan=z='{zexpr}':d={frames}:s=1280x720:"
          f"fps=24,format=yuv420p")
    run([
        "-loop", "1", "-i", str(img),
        "-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=48000",
        "-vf", vf, "-t", f"{dur}", "-r", "24",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
        "-shortest", str(out),
    ])


def main():
    # --- clip_02 系绳之约 : tender close moment from clip_01 (flower exchange) ---
    f2 = VID / "_px_frame_02.png"
    extract_frame(VID / "clip_01.mp4", 5.0, f2)
    zoomclip(f2, 9.0, VID / "clip_02_proxy.mp4", zoom_end=1.08)
    f2.unlink(missing_ok=True)
    print("MADE clip_02_proxy.mp4 (9s Ken Burns from clip_01)")

    # --- clip_06 荣归 : two sub-beats -> orchard he passes + his bow/release ---
    fa = VID / "_px_frame_06a.png"   # orchard establishing (clip_01 t=2)
    fb = VID / "_px_frame_06b.png"   # he bows / releases cord (clip_05 t=8)
    extract_frame(VID / "clip_01.mp4", 2.0, fa)
    extract_frame(VID / "clip_05.mp4", 8.0, fb)
    pa = VID / "_px_06a.mp4"
    pb = VID / "_px_06b.mp4"
    zoomclip(fa, 4.5, pa, zoom_end=1.05)
    zoomclip(fb, 4.5, pb, zoom_end=1.05)
    # concat the two halves
    lst = VID / "_px_concat.txt"
    lst.write_text(f"file '{pa.name}'\nfile '{pb.name}'\n", encoding="utf-8")
    run(["-f", "concat", "-safe", "0", "-i", str(lst),
         "-vf", "scale=1280:720,fps=24,format=yuv420p",
         "-c:v", "libx264", "-preset", "medium", "-crf", "20",
         "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
         str(VID / "clip_06_proxy.mp4")])
    for p in (fa, fb, pa, pb, lst):
        p.unlink(missing_ok=True)
    print("MADE clip_06_proxy.mp4 (9s: orchard zoom + bow/release zoom)")


if __name__ == "__main__":
    main()
