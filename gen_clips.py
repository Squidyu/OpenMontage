"""Generate the 7 Seedance clips for the 60s cinematic short
《上岸先斩意中人》 via the Volcengine ARK gateway (SeedanceARK tool).

Prompt style follows the `seedance-2-0` Layer-3 skill: 8-part template
(shot/framing + camera + subject + action beats + setting + lighting +
style/grade + audio), photorealistic 35mm, native audio ON for diegetic
environment sound (wind/rain/snow/hooves/flute).

Runs clip generations concurrently (ThreadPoolExecutor) to keep wall time
~ the longest single clip instead of 7x serial.
"""
from __future__ import annotations
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from tools.video.seedance_ark import SeedanceARK  # noqa: E402

PROJ = ROOT / "projects" / "shang-an-xian-zhan-yi-zhong-ren"
OUT = PROJ / "assets" / "video"
OUT.mkdir(parents=True, exist_ok=True)

SEED = 20260708  # fixed seed -> consistent visual temperature across shots

# 7 beats. duration in seconds (Seedance enum 4..10).
CLIPS = [
    {
        "name": "clip_01", "duration": 9,
        "prompt": (
            "[Medium wide shot, slow push-in] A young scholar in a weathered green robe "
            "reins his horse at the edge of a riverside peach orchard in spring, halting his "
            "journey; a red-clad village weaver steps forward and offers him a half-bundle of "
            "peach blossoms with a shy smile. "
            "[Action] 0-3s: scholar stops, mesmerized by the blossoms; 3-6s: weaver approaches "
            "and places the flowers into his hands; 6-9s: petals drift across warm golden light "
            "between them. "
            "[Setting] ancient Chinese water town, peach trees in full bloom, soft river mist. "
            "[Lighting] warm late-afternoon sunlight, volumetric haze, gentle halation on highlights. "
            "[Style] photorealistic, 35mm film grain, ARRI ALEXA aesthetic, soft highlight rolloff, "
            "authentic fabric detail, real skin pores. "
            "[Audio] distant water lapping, wind through petals, a soft non-diegetic guqin pluck. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_02", "duration": 9,
        "prompt": (
            "[Close-up, locked camera, shallow depth of field] Inside a dim oil-lamp room, a young "
            "woman in red hanfu lowers her gaze and ties a red cord bracelet around the wrist of a "
            "seated scholar in a green robe. "
            "[Action] 0-3s: she takes his wrist gently; 3-6s: loops the red string, fingers delicate; "
            "6-9s: he looks up, gazing at her profile, lantern light in his eyes. "
            "[Setting] wooden interior, paper window glow, a single oil lamp. "
            "[Lighting] intimate warm lamplight, low-key, deep shadows, candle flicker. "
            "[Style] photorealistic, 35mm, film grain, real skin pores, authentic fabric. "
            "[Audio] faint night insects, soft breathing, no music. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_03", "duration": 9,
        "prompt": (
            "[Wide shot, slow tracking] At an autumn pavilion by a rainy road, a scholar in green "
            "holds a paper umbrella; a red-clad woman hands him a cloth-wrapped travel satchel. "
            "[Action] 0-3s: rain falls on the tiled roof, he opens the umbrella; 3-6s: she steps "
            "forward through the rain and offers the bundle; 6-9s: they pause, fallen leaves swirl "
            "in the puddle. "
            "[Setting] ancient stone pavilion, yellowing trees, drizzle. "
            "[Lighting] overcast grey-blue, wet reflections, soft diffuse. "
            "[Style] photorealistic, 35mm, film grain, grounded reality. "
            "[Audio] steady rainfall on tile, distant thunder, cloth rustle. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_04", "duration": 10,
        "prompt": (
            "[Medium shot, slow push-in] A snowy night in the capital, a young scholar in a green "
            "robe bends over a desk by a frozen window, studying by candlelight, a red cord wrapped "
            "around his fingers. "
            "[Action] 0-3s: he writes, brush moving; 3-6s: touches the red cord at his wrist; "
            "6-10s: a letter slips from the desk and falls to the snow-dusted floor. "
            "[Setting] scholar's cold chamber, snow on the window lattice, stacks of books. "
            "[Lighting] cold blue moonlight mixed with warm candle, low-key, deep shadows. "
            "[Style] photorealistic, 35mm, film grain, real skin, authentic fabric. "
            "[Audio] wind through eaves, a faint distant bell, paper rustle. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_05", "duration": 9,
        "prompt": (
            "[Two-beat montage, implied cut] At the imperial exam results wall crowded with scholars, "
            "a green-robed man stares frozen at the posted list; later that night, a matchmaker's red "
            "thread pulls toward the lantern-lit mansion of the Prime Minister, and he lowers his eyes "
            "as the red cord at his wrist loosens. "
            "[Action] 0-4s: he reads the bulletin, stunned, crowd cheers around him; 4-9s: night, a "
            "shadowed matchmaker extends a red silk thread toward grand mansion lanterns, he bows his "
            "head, fingers release the cord. "
            "[Setting] bustling bulletin square then opulent mansion gate. "
            "[Lighting] day bright then night warm lantern glow, chiaroscuro. "
            "[Style] photorealistic, 35mm, film grain, authentic fabric. "
            "[Audio] crowd murmur then silence, distant lantern wind, a single low drum. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_06", "duration": 9,
        "prompt": (
            "[Wide tracking shot then cut to interior] A scholar now in fine embroidered official "
            "robes rides a horse past the orchard entrance, reins pulled to veer away; behind a lattice "
            "window, a still red-clad figure stands, then raises her hand and unties the red cord at her "
            "own wrist. "
            "[Action] 0-4s: him on horse, slows, turns his face aside, rides past without stopping; "
            "4-9s: her at the window, calm, unwinds the red bracelet and lets it drop. "
            "[Setting] peach orchard lane then dim interior by window. "
            "[Lighting] bright daylight outside, muted interior, emotional restraint. "
            "[Style] photorealistic, 35mm, film grain, real skin, authentic fabric. "
            "[Audio] horse hooves on earth, then silence, fabric slip. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
    {
        "name": "clip_07", "duration": 5,
        "prompt": (
            "[Extreme wide, static] A red cord drifts on a slow mountain stream and is carried away; "
            "peach blossoms fall and wither on the water's surface, an empty landscape with no people. "
            "[Action] 0-5s: the cord floats downstream, petals settle and dissolve, nothing else moves. "
            "[Setting] quiet stream through bare peach branches. "
            "[Lighting] soft dusk, melancholic, muted warm. "
            "[Style] photorealistic, 35mm, film grain, poetic. "
            "[Audio] gentle water, wind, a fading lone flute note. "
            "no 3D, no cartoon, no VFX aesthetic."
        ),
    },
]


def generate(clip: dict):
    tool = SeedanceARK()
    params = {
        "prompt": clip["prompt"],
        "operation": "text_to_video",
        "duration": clip["duration"],
        "aspect_ratio": "16:9",
        "resolution": "720p",
        "generate_audio": True,
        "seed": SEED,
        "output_path": str(OUT / f'{clip["name"]}.mp4'),
    }
    t0 = time.time()
    res = tool.execute(params)
    dt = round(time.time() - t0, 1)
    return clip["name"], res, dt


def main():
    print(f"Launching {len(CLIPS)} Seedance clips (concurrent) -> {OUT}")
    results = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futs = {ex.submit(generate, c): c["name"] for c in CLIPS}
        for fut in as_completed(futs):
            name, res, dt = fut.result()
            if res.success:
                d = res.data or {}
                print(f"  [OK]   {name}  {dt}s  -> {d.get('output')}  "
                      f"({d.get('duration_seconds')}s video)")
                results[name] = "ok"
            else:
                print(f"  [FAIL] {name}  {dt}s  -> {res.error}")
                results[name] = f"fail: {res.error}"
    ok = sum(1 for v in results.values() if v == "ok")
    print(f"GENERATION_DONE ok={ok}/{len(CLIPS)}")
    # write a tiny manifest status
    (PROJ / "artifacts" / "_gen_status.json").write_text(
        __import__("json").dumps(results, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
