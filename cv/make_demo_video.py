"""CV demo video (10 s, English): title card, 5 automated tests, end card.

Usage: python cv/make_demo_video.py  ->  cv/testing-factory-demo.mp4
Reads the per-test videos recorded by Playwright (automation/test-results/results.json).
"""
import json
import subprocess
from pathlib import Path

import imageio_ffmpeg

HERE = Path(__file__).resolve().parent
RESULTS = HERE.parent / "automation" / "test-results" / "results.json"
OUT = HERE / "testing-factory-demo.mp4"
BOLD = "C\\:/Windows/Fonts/segoeuib.ttf"
REG = "C\\:/Windows/Fonts/segoeui.ttf"
NAVY, ORANGE = "0x1B2340", "0xC9541F"
W, H, FPS = 1280, 720, 25
CARD, CLIP = 1.5, 1.4  # 1.5 + 5 x 1.4 + 1.5 = 10 s

# Xray test key -> English caption shown in the video (keys themselves are not shown).
SCENES = [
    ("SCRUM-102", "Home page loads"),
    ("SCRUM-104", "Search with no match"),
    ("SCRUM-105", "Add a product to the cart"),
    ("SCRUM-108", "Invalid login is rejected"),
    ("SCRUM-109", "Create and delete an account"),
]


def videos():
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


def text(name, content, work):
    (work / name).write_text(content, encoding="utf-8")
    return f".tmp/{name}"


def main():
    work = HERE / ".tmp"
    work.mkdir(exist_ok=True)
    found = videos()
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    parts, labels = [], []

    # Title card
    cmd += ["-f", "lavfi", "-t", str(CARD), "-i", f"color=c={NAVY}:s={W}x{H}:r={FPS}"]
    t1, t2, t3 = (text("t1.txt", "Testing Factory", work),
                  text("t2.txt", "An AI agent that tests a website end to end", work),
                  text("t3.txt", "from a user story to the test report", work))
    parts.append(
        f"[0:v]drawbox=x=96:y=250:w=90:h=8:color={ORANGE}:t=fill,"
        f"drawtext=fontfile='{BOLD}':textfile='{t1}':x=96:y=280:fontsize=84:fontcolor=white,"
        f"drawtext=fontfile='{REG}':textfile='{t2}':x=96:y=400:fontsize=36:fontcolor=0xF6F4EF,"
        f"drawtext=fontfile='{REG}':textfile='{t3}':x=96:y=452:fontsize=36:fontcolor=0x9BA3B8,"
        f"fade=t=out:st={CARD - 0.25}:d=0.25,format=yuv420p[c0]")
    labels.append("[c0]")

    # Test clips
    for i, (key, caption) in enumerate(SCENES, start=1):
        video, duration, status = found[key]
        if status != "expected":
            raise SystemExit(f"{key} did not pass in the last run: rerun the tests first")
        skip = min(1.2, duration * 0.3)
        speed = CLIP / max(duration - skip, CLIP)
        cmd += ["-i", video]
        cap = text(f"c{i}.txt", caption, work)
        step = text(f"s{i}.txt", f"Automated test {i}/5", work)
        parts.append(
            f"[{i}:v]trim=start={skip:.2f},setpts=PTS-STARTPTS,setpts=PTS*{speed:.4f},"
            f"fps={FPS},scale={W}:{H},tpad=stop_mode=clone:stop_duration={CLIP},"
            f"trim=duration={CLIP},setpts=PTS-STARTPTS,"
            f"drawbox=x=0:y=ih-64:w=iw:h=64:color={NAVY}@0.94:t=fill,"
            f"drawtext=fontfile='{REG}':textfile='{step}':x=24:y=h-50:fontsize=18:fontcolor=0x9BA3B8,"
            f"drawtext=fontfile='{BOLD}':textfile='{cap}':x=220:y=h-48:fontsize=28:fontcolor=white,"
            f"drawbox=x=iw-170:y=ih-52:w=146:h=40:color=0x2E9E62:t=fill,"
            f"drawtext=fontfile='{BOLD}':text='PASSED':x=w-97-text_w/2:y=h-46:fontsize=22:fontcolor=white,"
            f"format=yuv420p[c{i}]")
        labels.append(f"[c{i}]")

    # End card
    n = len(SCENES) + 1
    cmd += ["-f", "lavfi", "-t", str(CARD), "-i", f"color=c={NAVY}:s={W}x{H}:r={FPS}"]
    e1 = text("e1.txt", "Jira  →  Xray  →  Playwright  →  Report", work)
    e2 = text("e2.txt", "Test plan, tests, automation and run: all done by the AI agent", work)
    parts.append(
        f"[{n}:v]drawtext=fontfile='{BOLD}':textfile='{e1}':x=(w-text_w)/2:y=290:fontsize=54:fontcolor=white,"
        f"drawbox=x=(iw-90)/2:y=380:w=90:h=8:color={ORANGE}:t=fill,"
        f"drawtext=fontfile='{REG}':textfile='{e2}':x=(w-text_w)/2:y=410:fontsize=30:fontcolor=0xC9CFDD,"
        f"fade=t=in:st=0:d=0.25,format=yuv420p[c{n}]")
    labels.append(f"[c{n}]")

    graph = ";".join(parts) + ";" + "".join(labels) + f"concat=n={len(labels)}:v=1:a=0[out]"
    (work / "graph.txt").write_text(graph, encoding="utf-8")
    cmd += ["-filter_complex_script", ".tmp/graph.txt", "-map", "[out]", "-an", "-c:v", "libx264",
            "-preset", "slow", "-crf", "23", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT.name]
    proc = subprocess.run(cmd, cwd=HERE, capture_output=True, text=True, encoding="utf-8")
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    if proc.returncode != 0:
        raise SystemExit(proc.stderr[-800:])
    print(OUT)


if __name__ == "__main__":
    main()
