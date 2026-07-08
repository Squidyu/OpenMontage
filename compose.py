"""Compose the 7 generated clips into the final 60s cinematic short.

Pipeline: ffmpeg runtime (locked in edit_decisions.render_runtime).
- each clip normalized to 1920x1080, yuv420p, 24fps
- cross-fade (xfade) 0.6s between consecutive clips
- 2.35:1 cinematic letterbox (content 1920x816, pillarbox-free top/bottom bars)
- ancient-Chinese title captions burned via drawtext (STXINGKA / STKAITI)
- native diegetic audio cross-faded (acrossfade) and mixed to AAC
- faststart + yuv420p (plays on the user's VLC / WMP without the stall)
"""
from __future__ import annotations
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROJ = ROOT / "projects" / "shang-an-xian-zhan-yi-zhong-ren"
OUT = PROJ / "assets" / "video"
REND = PROJ / "renders"
REND.mkdir(parents=True, exist_ok=True)

FF = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"
FFP = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffprobe.exe"
FT_TITLE = r"'C\:\\Windows\\Fonts\\STXINGKA.TTF'"   # 华文行楷
FT_BODY = r"'C\:\\Windows\\Fonts\\STKAITI.TTF'"     # 华文楷体
XF = 0.6

def clip_path(i: int) -> Path:
    real = OUT / f"clip_{i:02d}.mp4"
    if real.exists():
        return real
    proxy = OUT / f"clip_{i:02d}_proxy.mp4"
    if proxy.exists():
        return proxy
    raise SystemExit(f"missing clip_{i:02d}.mp4 and no proxy")


clips = [clip_path(i) for i in range(1, 8)]
for i, c in enumerate(clips, start=1):
    tag = "REAL" if c.name == f"clip_{i:02d}.mp4" else "PROXY"
    print(f"  beat {i:02d}: {tag} {c.name}")


def probe_dur(p: Path) -> float:
    o = subprocess.check_output(
        [FFP, "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(p)],
        stderr=subprocess.STDOUT,
    )
    return float(o.strip())


durs = [probe_dur(c) for c in clips]

# cumulative clip start on the final timeline (xfade overlap shortens gaps)
starts: list[float] = []
acc = 0.0
for d in durs:
    starts.append(acc)
    acc += d - XF

# ---- video filter graph ----
fcp: list[str] = []
for i in range(len(clips)):
    fcp.append(
        f"[{i}:v]scale=1920:1080:force_original_aspect_ratio=decrease,"
        f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p[v{i}]"
    )

cur = "[v0]"
offset = durs[0] - XF
for i in range(1, len(clips)):
    fcp.append(
        f"{cur}[v{i}]xfade=transition=fade:duration={XF}:offset={offset:.3f}[x{i}]"
    )
    cur = f"[x{i}]"
    offset += durs[i] - XF

# 2.35:1 letterbox -> content 1920x816 centered in 1920x1080
fcp.append(
    f"{cur}scale=1920:816:force_original_aspect_ratio=decrease,"
    f"pad=1920:1080:(ow-iw)/2:(oh-ih)/2[base]"
)

# ---- burned captions (ancient Chinese, timed per beat) ----
subs = [
    ("桃坞春深　半束花　一笑误终身", FT_BODY, 60, "h*0.80"),
    ("腕上红绳　金榜之约", FT_BODY, 60, "h*0.80"),
    ("此去京华　君勿相忘", FT_BODY, 60, "h*0.80"),
    ("雪夜家书：母病，坞中已许富商", FT_BODY, 52, "h*0.80"),
    ("一纸功名　千斤门槛", FT_BODY, 60, "h*0.80"),
    ("锦衣过门不入　红绳自解", FT_BODY, 60, "h*0.80"),
    ("上岸先斩意中人", FT_TITLE, 104, "h*0.42"),
]
label = "[base]"
for i, (txt, ft, sz, y) in enumerate(subs):
    s = starts[i] + 0.4
    e = starts[i] + durs[i] - 0.4
    nxt = "[vout]" if i == len(subs) - 1 else f"[s{i}]"
    fcp.append(
        f"{label}drawtext=fontfile={ft}:text='{txt}':"
        f"fontcolor=#F3E0B5:fontsize={sz}:x=(w-tw)/2:y={y}:"
        f"shadowcolor=black@0.65:shadowx=4:shadowy=4:"
        f"enable='between(t,{s:.2f},{e:.2f})'{nxt}"
    )
    label = nxt

# ---- audio cross-fade chain ----
acp: list[str] = []
acur = "[0:a]"
for i in range(1, len(clips)):
    nxt = f"[a{i}]"
    acp.append(f"{acur}[{i}:a]acrossfade=d={XF}{nxt}")
    acur = nxt
aout = acur

fc = ";".join(fcp + acp)

cmd = [FF, "-y"]
for c in clips:
    cmd += ["-i", str(c)]
cmd += [
    "-filter_complex", fc,
    "-map", "[vout]", "-map", aout,
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-maxrate", "8M", "-bufsize", "16M",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
    "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
    "-movflags", "+faststart",
    str(REND / "final.mp4"),
]

print("Running ffmpeg compose (ffmpeg runtime)...")
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("rc=", r.returncode)
print((r.stderr or "")[-3000:])
if r.returncode == 0:
    print("COMPOSE_DONE ->", str(REND / "final.mp4"))
else:
    print("COMPOSE_FAILED")
