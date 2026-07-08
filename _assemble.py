"""Assemble the 15s classical short: concat clip A(7s)+B(8s) with an xfade,
overlay classical Chinese captions via drawtext (full ffmpeg build)."""
import subprocess
from pathlib import Path

OUT = Path("output")
FFMPEG = r"C:\Users\squidxu\ffmpeg\ffmpeg-8.1.2-full_build\bin\ffmpeg.exe"

# Fonts: canonical Windows drawtext form -> single quotes + \:\\ escaping
FT_TITLE = r"'C\:\\Windows\\Fonts\\STXINGKA.TTF'"   # 华文行楷
FT_BODY = r"'C\:\\Windows\\Fonts\\STKAITI.TTF'"     # 华文楷体

fc = (
    "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p[va];"
    "[1:v]scale=1280:720:force_original_aspect_ratio=decrease,"
    "pad=1280:720:(ow-iw)/2:(oh-ih)/2,fps=24,format=yuv420p[vb];"
    "[va][vb]xfade=transition=fade:duration=0.6:offset=6.4[base];"
    f"[base]drawtext=fontfile={FT_TITLE}:text='上岸先斩意中人':"
    "fontcolor=#F3E0B5:fontsize=104:x=(w-tw)/2:y=h*0.30:"
    "shadowcolor=black@0.6:shadowx=4:shadowy=4:enable='between(t,0.3,3.4)'[p1];"
    f"[p1]drawtext=fontfile={FT_BODY}:text='— 古风短片 · 十五秒 —':"
    "fontcolor=#DCD2BE:fontsize=40:x=(w-tw)/2:y=h*0.30+120:"
    "shadowcolor=black@0.6:shadowx=3:shadowy=3:enable='between(t,0.3,3.4)'[p2];"
    f"[p2]drawtext=fontfile={FT_BODY}:text='寒窗十载 · 终跃龙门':"
    "fontcolor=#F5EEDC:fontsize=56:x=(w-tw)/2:y=h-th-80:"
    "shadowcolor=black@0.7:shadowx=3:shadowy=3:enable='between(t,3.6,6.9)'[p3];"
    f"[p3]drawtext=fontfile={FT_BODY}:text='却道：功名既得，斩情以行':"
    "fontcolor=#F5EEDC:fontsize=56:x=(w-tw)/2:y=h-th-80:"
    "shadowcolor=black@0.7:shadowx=3:shadowy=3:enable='between(t,7.3,14.4)'[vout];"
    "[0:a][1:a]acrossfade=d=0.6[aout]"
)

cmd = [
    FFMPEG, "-y",
    "-i", str(OUT / "clip_A.mp4"),
    "-i", str(OUT / "clip_B.mp4"),
    "-filter_complex", fc,
    "-map", "[vout]", "-map", "[aout]",
    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
    "-maxrate", "8M", "-bufsize", "16M",
    "-pix_fmt", "yuv420p", "-profile:v", "high", "-level", "4.0",
    "-c:a", "aac", "-b:a", "192k",
    "-movflags", "+faststart",
    str(OUT / "上岸先斩意中人_420p.mp4"),
]
print("Running ffmpeg (full build)...")
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("rc=", r.returncode)
print((r.stderr or "")[-2500:])
if r.returncode == 0:
    print("DONE ->", str(OUT / "上岸先斩意中人_420p.mp4"))
else:
    print("FAILED")
