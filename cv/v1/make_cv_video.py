"""CV video (English, ~28 s): intro, tech-stack diagram, Jira/Xray screens, Playwright demo, end card.

Inputs:
  cv/.frames/intro, cv/.frames/stack  -> PNG frames from automation/scripts/render-scene.mjs
  cv/.captures/*.png                  -> Jira/Xray captures from automation/scripts/capture-jira.mjs
  automation/test-results/results.json -> Playwright videos of the last run
Output: cv/amine-bouchghoul-testing-factory.mp4
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
SHOT, CLIP, END, REPORT = 1.75, 1.2, 2.0, 2.4
REPORT_SHOT = ("5-report.png", "Report", "The PDF test report, sent on Telegram and by email")

# Animated scenes shown before the Jira/Xray captures, in order (cv/scenes/<name>.html).
SCENE_ORDER = ("intro", "stack", "workflow", "inside", "trace", "always")

CAPTURES = [
    ("1-story.png", "Jira", "The backlog: user stories and bugs the agent reads"),
    ("2-test.png", "Xray", "A test case written by the agent, with its steps"),
    ("3-gherkin.png", "Gherkin", "The BDD scenario the agent writes for every test"),
    ("4-testplan.png", "Jira", "118 tickets managed in the project"),
]
SCENES = [
    ("SCRUM-102", "Home page loads"),
    ("SCRUM-104", "Search with no match"),
    ("SCRUM-105", "Add a product to the cart"),
    ("SCRUM-108", "Invalid login is rejected"),
    ("SCRUM-109", "Create and delete an account"),
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

    def bar(label, caption, idx, top=False):
        """Bottom caption bar: orange tag + white caption."""
        tag = txt(f"tag{idx}.txt", label)
        cap = txt(f"cap{idx}.txt", caption)
        return (f"drawbox=x=0:y=ih-70:w=iw:h=70:color={NAVY}@0.95:t=fill,"
                f"drawbox=x=24:y=ih-54:w=128:h=38:color={ORANGE}:t=fill,"
                f"drawtext=fontfile='{BOLD}':textfile='{tag}':x=24+64-text_w/2:y=h-48:fontsize=22:fontcolor=white,"
                f"drawtext=fontfile='{BOLD}':textfile='{cap}':x=172:y=h-50:fontsize=27:fontcolor=white")

    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    parts, labels, n = [], [], 0

    # 1-2. Animated scenes rendered frame by frame
    for scene in SCENE_ORDER:
        cmd += ["-framerate", str(FPS), "-i", str(HERE / ".frames" / scene / "f%04d.png")]
        parts.append(f"[{n}:v]scale={W}:{H},format=yuv420p[v{n}]")
        labels.append(f"[v{n}]"); n += 1

    def still(file, tag, caption, idx, seconds, y_anchor="ih/3-(ih/zoom/3)"):
        """A high-res capture with a slow zoom and a caption bar."""
        nonlocal n, cmd
        path = HERE / ".captures" / file
        if not path.exists():
            raise SystemExit(f"missing capture {path}")
        frames = round(seconds * FPS)
        cmd += ["-i", str(path)]
        parts.append(
            f"[{n}:v]scale=2560:1440,zoompan=z='1+0.05*on/{frames}':x='iw/2-(iw/zoom/2)':"
            f"y='{y_anchor}':d={frames}:s={W}x{H}:fps={FPS},"
            f"{bar(tag, caption, idx)},fade=t=in:st=0:d=0.2,format=yuv420p[v{n}]")
        labels.append(f"[v{n}]"); n += 1

    # 3. Jira / Xray captures with a slow zoom
    for i, (file, tag, caption) in enumerate(CAPTURES):
        still(file, tag, caption, i, SHOT)

    # 4a. Gherkin -> Playwright scene
    cmd += ["-framerate", str(FPS), "-i", str(HERE / ".frames" / "playwright" / "f%04d.png")]
    parts.append(f"[{n}:v]scale={W}:{H},format=yuv420p[v{n}]")
    labels.append(f"[v{n}]"); n += 1

    # 4b. Playwright demo clips
    found = test_videos()
    for i, (key, caption) in enumerate(SCENES, start=1):
        video, duration, status = found[key]
        if status != "expected":
            raise SystemExit(f"{key} did not pass in the last run: rerun the tests first")
        skip = min(1.2, duration * 0.3)
        speed = CLIP / max(duration - skip, CLIP)
        cmd += ["-i", video]
        step = txt(f"s{i}.txt", f"Test {i}/5")
        cap = txt(f"c{i}.txt", caption)
        parts.append(
            f"[{n}:v]trim=start={skip:.2f},setpts=PTS-STARTPTS,setpts=PTS*{speed:.4f},"
            f"fps={FPS},scale={W}:{H},tpad=stop_mode=clone:stop_duration={CLIP},"
            f"trim=duration={CLIP},setpts=PTS-STARTPTS,"
            f"drawbox=x=0:y=ih-70:w=iw:h=70:color={NAVY}@0.95:t=fill,"
            f"drawbox=x=24:y=ih-54:w=128:h=38:color={ORANGE}:t=fill,"
            f"drawtext=fontfile='{BOLD}':text='LIVE RUN':x=24+64-text_w/2:y=h-48:fontsize=20:fontcolor=white,"
            f"drawtext=fontfile='{REG}':textfile='{step}':x=172:y=h-46:fontsize=21:fontcolor=0x9BA3B8,"
            f"drawtext=fontfile='{BOLD}':textfile='{cap}':x=262:y=h-50:fontsize=27:fontcolor=white,"
            f"drawbox=x=iw-176:y=ih-54:w=152:h=38:color=0x2E9E62:t=fill,"
            f"drawtext=fontfile='{BOLD}':text='PASSED':x=w-100-text_w/2:y=h-48:fontsize=22:fontcolor=white,"
            f"format=yuv420p[v{n}]")
        labels.append(f"[v{n}]"); n += 1

    # 5. PDF report capture, zooming toward the top of the page
    still(*REPORT_SHOT, idx=9, seconds=REPORT, y_anchor="0")

    # 6. End card
    cmd +=["-f", "lavfi", "-t", str(END), "-i", f"color=c={NAVY}:s={W}x{H}:r={FPS}"]
    e1 = txt("e1.txt", "Amine Bouchghoul")
    e2 = txt("e2.txt", "QA / Lead QA Engineer  ·  AI-driven test automation")
    e3 = txt("e3.txt", "Testing Factory: user story & bug in, tested, automated and reported out")
    parts.append(
        f"[{n}:v]drawbox=x=(iw-96)/2:y=250:w=96:h=8:color={ORANGE}:t=fill,"
        f"drawtext=fontfile='{BOLD}':textfile='{e1}':x=(w-text_w)/2:y=285:fontsize=68:fontcolor=white,"
        f"drawtext=fontfile='{REG}':textfile='{e2}':x=(w-text_w)/2:y=385:fontsize=30:fontcolor=0xC9CFDD,"
        f"drawtext=fontfile='{REG}':textfile='{e3}':x=(w-text_w)/2:y=440:fontsize=24:fontcolor=0x8790A8,"
        f"fade=t=in:st=0:d=0.3,format=yuv420p[v{n}]")
    labels.append(f"[v{n}]"); n += 1

    # 7. Background music (original, generated by make_music.py to the exact length)
    total = sum(len(list((HERE / ".frames" / s).glob("f*.png"))) for s in SCENE_ORDER) / FPS + len(CAPTURES) * SHOT + 3.2 + len(SCENES) * CLIP + REPORT + END
    subprocess.run([sys.executable, str(HERE / "make_music.py"), f"{total:.2f}"], check=True,
                   capture_output=True)
    cmd += ["-i", str(HERE / ".music.wav")]
    parts.append(f"[{n}:a]loudnorm=I=-20:TP=-2:LRA=11,aformat=sample_rates=48000[aout]")

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
        raise SystemExit(proc.stderr[-1200:])
    print(OUT)


if __name__ == "__main__":
    main()
