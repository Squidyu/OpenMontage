"""Generate the two Seedance clips for the 15s classical short '上岸先斩意中人'."""
import json
import sys
from pathlib import Path
from tools.video.seedance_ark import SeedanceARK

OUT = Path("output")
OUT.mkdir(exist_ok=True)

tool = SeedanceARK()

clips = [
    {
        "name": "A",
        "output_path": str(OUT / "clip_A.mp4"),
        "duration": 7,
        "prompt": (
            "古风水墨动画，中国古代书生寒窗苦读多年后金榜题名，身着锦袍在朱红府邸回廊驻足，"
            "远处一袭白衣女子倚窗凝望，暖色夕阳洒落，工笔重彩，电影感运镜，唯美古典意境"
        ),
    },
    {
        "name": "B",
        "output_path": str(OUT / "clip_B.mp4"),
        "duration": 8,
        "prompt": (
            "古风水墨动画，书生背对镜头决绝转身离去，手中红绳寸寸断裂飘落，白衣女子怔立窗前，"
            "秋叶纷飞，凄凉古典意境，电影感慢镜头，工笔重彩，留白美学"
        ),
    },
]

log = OUT / "clips_status.json"
results = {}
for c in clips:
    sys.stderr.write(f"\n=== Generating clip {c['name']} ({c['duration']}s) ===\n")
    sys.stderr.flush()
    r = tool.execute({
        "prompt": c["prompt"],
        "operation": "text_to_video",
        "duration": c["duration"],
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "generate_audio": True,
        "output_path": c["output_path"],
    })
    if r.success:
        results[c["name"]] = r.data
        sys.stderr.write(f"OK clip {c['name']} -> {r.data['output']} ({r.data.get('duration_seconds')}s)\n")
    else:
        sys.stderr.write(f"FAIL clip {c['name']}: {r.error}\n")
    sys.stderr.flush()

log.write_text(json.dumps(results, ensure_ascii=False, indent=2))
print("CLIPS_DONE", json.dumps({k: v.get("output") for k, v in results.items()}, ensure_ascii=False))
