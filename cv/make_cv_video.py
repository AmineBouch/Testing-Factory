"""CV video v2 (English, ~3 min, calm pacing).

Order: intro & architecture scenes -> Jira/Xray captures -> human-on-the-loop diagrams
-> Gherkin/Playwright scene -> live run on saucedemo.com -> Slack reporting -> end card.

Inputs:
  cv/.frames/<scene>/f%04d.png        -> frames from automation/scripts/render-scene.mjs (cv/scenes/<scene>.html)
  cv/.captures/*.png                  -> Jira/Xray captures from automation/scripts/capture-jira.mjs
  automation/test-results/results.json -> Playwright videos of the last saucedemo run (@saucedemo)
Output: cv/amine-bouchghoul-testing-factory.mp4   (previous version kept in cv/v1/)
"""
import json
import subprocess
import sys
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "automation" / "test-results" / "results.json"
OUT = HERE / "amine-bouchghoul-testing-factory.mp4"
BOLD = "C\\:/Windows/Fonts/segoeuib.ttf"
REG = "C\\:/Windows/Fonts/segoeui.ttf"
NAVY, ORANGE = "0x141B2E", "0xE0713A"
W, H, FPS = 1280, 720, 25
SHOT = 3.5     # seconds per Jira/Xray capture
SPEED = 1.2    # saucedemo clips: barely faster than real time
SKIP = 0.4     # blank page at the start of each Playwright video
END = 5.0

INTRO_SCENES = ("intro", "stack", "workflow", "inside", "trace", "always")
CAPTURES = [
    ("1-story.png", "Jira", "The backlog: user stories and bugs the agent reads"),
    ("2-test.png", "Xray", "A test case written by the agent, with its steps"),
    ("3-gherkin.png", "Gherkin", "The BDD scenario the agent writes for every test"),
    ("4-testplan.png", "Jira", "118 tickets managed in the project"),
]
HOTL_SCENES = ("hotl-intro", "hotl-review", "hotl-guardrails", "hotl-po", "hotl-bugs", "hotl-digest")
CLIPS = [
    ("SD-1", "A standard user logs in and sees the catalogue"),
    ("SD-2", "A locked-out user is refused with a clear message"),
    ("SD-3", "Sort by price, add two products to the cart"),
    ("SD-4", "Full checkout, up to the order confirmation"),
]


def test_videos():
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    found = {}

    def walk(suite):
        for spec in suite.get("specs", []):
            for test in spec["tests"]:
                last = test["results"][-1]
                video = next((a["path"] for a in last.get("attachments", [])
                              if a.get("contentType", "").startswith("video/")), None)
                found[spec["tags"][-1]] = (video, last["duration"] / 1000, test["status"])
        for child in suite.get("suites", []):
            walk(child)

    for s in data["suites"]:
        walk(s)
    return found


def main():
    work = HERE / ".tmp"
    work.mkdir(exist_ok=True)

    def txt(name, content):
        (work / name).write_text(content, encoding="utf-8")
        return f".tmp/{name}"

    def bar(label, caption, idx):
        """Bottom caption bar: orange tag + white caption."""
        tag = txt(f"tag{idx}.txt", label)
        cap = txt(f"cap{idx}.txt", caption)
        return (f"drawbox=x=0:y=ih-70:w=iw:h=70:color={NAVY}@0.95:t=fill,"
                f"drawbox=x=24:y=ih-54:w=128:h=38:color={ORANGE}:t=fill,"
                f"drawtext=fontfile='{BOLD}':textfile='{tag}':x=24+64-text_w/2:y=h-48:fontsize=22:fontcolor=white,"
                f"drawtext=fontfile='{BOLD}':textfile='{cap}':x=172:y=h-50:fontsize=27:fontcolor=white")

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    parts, labels = [], []
    total = 0.0
    n = 0

    def add(chain):
        nonlocal n
        parts.append(chain.replace("[IN]", f"[{n}:v]") + f"[v{n}]")
        labels.append(f"[v{n}]")
        n += 1

    def scene(name):
        nonlocal cmd, total
        frames = HERE / ".frames" / name
        count = len(list(frames.glob("f*.png")))
        if not count:
            raise SystemExit(f"no frames for {name}: render cv/scenes/{name}.html first")
        cmd += ["-framerate", str(FPS), "-i", str(frames / "f%04d.png")]
        add(f"[IN]scale={W}:{H},fade=t=in:st=0:d=0.25,format=yuv420p")
        total += count / FPS

    def still(file, tag, caption, idx, seconds):
        """A high-res capture with a slow zoom and a caption bar."""
        nonlocal cmd, total
        path = HERE / ".captures" / file
        if not path.exists():
            raise SystemExit(f"missing capture {path}")
        frames = round(seconds * FPS)
        cmd += ["-i", str(path)]
        add(f"[IN]scale=2560:1440,zoompan=z='1+0.06*on/{frames}':x='iw/2-(iw/zoom/2)':"
            f"y='ih/3-(ih/zoom/3)':d={frames}:s={W}x{H}:fps={FPS},"
            f"{bar(tag, caption, idx)},fade=t=in:st=0:d=0.3,format=yuv420p")
        total += seconds

    # 1. Who I am and how the agent is built
    for name in INTRO_SCENES:
        scene(name)

    # 2. Jira / Xray captures
    for i, (file, tag, caption) in enumerate(CAPTURES):
        still(file, tag, caption, i, SHOT)

    # 3. Human on the loop
    for name in HOTL_SCENES:
        scene(name)

    # 4. Gherkin -> Playwright, then the live run on saucedemo.com
    scene("playwright")
    found = test_videos()
    for i, (key, caption) in enumerate(CLIPS, start=1):
        if key not in found:
            raise SystemExit(f"{key} not in the last run: run `npx playwright test --grep @saucedemo` first")
        video, duration, status = found[key]
        if status != "expected":
            raise SystemExit(f"{key} did not pass in the last run: rerun the tests first")
        length = round((duration - SKIP) / SPEED, 2)
        cmd += ["-i", video]
        step = txt(f"s{i}.txt", f"Test {i}/{len(CLIPS)}")
        cap = txt(f"c{i}.txt", caption)
        add(f"[IN]trim=start={SKIP},setpts=(PTS-STARTPTS)/{SPEED},fps={FPS},scale={W}:{H},"
            f"tpad=stop_mode=clone:stop_duration=2,trim=duration={length},setpts=PTS-STARTPTS,"
            f"drawbox=x=0:y=ih-70:w=iw:h=70:color={NAVY}@0.95:t=fill,"
            f"drawbox=x=24:y=ih-54:w=128:h=38:color={ORANGE}:t=fill,"
            f"drawtext=fontfile='{BOLD}':text='LIVE RUN':x=24+64-text_w/2:y=h-48:fontsize=20:fontcolor=white,"
            f"drawtext=fontfile='{REG}':textfile='{step}':x=172:y=h-46:fontsize=21:fontcolor=0x9BA3B8,"
            f"drawtext=fontfile='{BOLD}':textfile='{cap}':x=262:y=h-50:fontsize=26:fontcolor=white,"
            f"drawbox=x=iw-176:y=ih-54:w=152:h=38:color=0x2E9E62:t=fill:enable='gte(t,{length - 1.6})',"
            f"drawtext=fontfile='{BOLD}':text='PASSED':x=w-100-text_w/2:y=h-48:fontsize=22:fontcolor=white:enable='gte(t,{length - 1.6})',"
            f"fade=t=in:st=0:d=0.3,format=yuv420p")
        total += length

    # 5. Results reported in Slack
    scene("slack-report")

    # 6. End card
    cmd += ["-f", "lavfi", "-t", str(END), "-i", f"color=c={NAVY}:s={W}x{H}:r={FPS}"]
    e1 = txt("e1.txt", "Amine Bouchghoul")
    e2 = txt("e2.txt", "QA / Lead QA Engineer  ·  AI-driven test automation")
    e3 = txt("e3.txt", "Testing Factory: automated by an AI agent, supervised by a human")
    add(f"[IN]drawbox=x=(iw-96)/2:y=250:w=96:h=8:color={ORANGE}:t=fill,"
        f"drawtext=fontfile='{BOLD}':textfile='{e1}':x=(w-text_w)/2:y=285:fontsize=68:fontcolor=white,"
        f"drawtext=fontfile='{REG}':textfile='{e2}':x=(w-text_w)/2:y=385:fontsize=30:fontcolor=0xC9CFDD,"
        f"drawtext=fontfile='{REG}':textfile='{e3}':x=(w-text_w)/2:y=440:fontsize=24:fontcolor=0x8790A8,"
        f"fade=t=in:st=0:d=0.4,fade=t=out:st={END - 0.8}:d=0.8,format=yuv420p")
    total += END

    # 7. Background music (original, generated by make_music.py to the exact length)
    subprocess.run([sys.executable, str(HERE / "make_music.py"), f"{total:.2f}"], check=True,
                   capture_output=True)
    cmd += ["-i", str(HERE / ".music.wav")]
    parts.append(f"[{n}:a]loudnorm=I=-20:TP=-2:LRA=11,afade=t=out:st={total - 2:.2f}:d=2,"
                 f"aformat=sample_rates=48000[aout]")

    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=1:a=0[out]"
    (work / "graph.txt").write_text(graph, encoding="utf-8")
    cmd += ["-filter_complex_script", ".tmp/graph.txt", "-map", "[out]", "-map", "[aout]",
            "-c:v", "libx264", "-preset", "slow", "-crf", "21", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "160k", "-shortest", "-movflags", "+faststart", OUT.name]
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    if proc.returncode != 0:
        raise SystemExit(proc.stderr[-1500:])
    print(f"{OUT}  ({total:.1f} s)")


if __name__ == "__main__":
    main()
