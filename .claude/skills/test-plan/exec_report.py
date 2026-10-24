"""Rapport d'exécution automatisée (Playwright) : génération + envoi email, Slack et Teams.

Lit automation/test-results/results.json (reporter JSON de Playwright), écrit
reports/execution-playwright-AAAA-MM-JJ-HHMM.md puis l'envoie via
mailer.py, slack.py et teams.py (identifiants dans .env, jamais affichés).

Convention : chaque scénario porte les tags Xray @SCRUM-<story> (sur la Feature)
et @SCRUM-<test> (sur le Scénario) ; le dernier tag SCRUM-x est la clé du Test.

Usage :
    python exec_report.py                     # génère + envoie
    python exec_report.py --no-send           # génère seulement
    python exec_report.py --plan SCRUM-118    # précise le Test Plan dans l'en-tête
    python exec_report.py --lang en           # PDF en anglais (…-en.pdf)

Affiche un JSON (chemin du rapport, compteurs, résultat des envois).
"""

import base64
import html
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RESULTS = ROOT / "automation" / "test-results" / "results.json"
REPORTS = ROOT / "reports"
JIRA = "https://testingfactory2026.atlassian.net/browse/"
ANSI = re.compile(r"\x1b\[[0-9;]*m")
ICON = {"PASS": "✅ PASS", "FLAKY": "⚠️ PASS (instable)", "FAIL": "❌ **FAIL**", "SKIP": "⏭️ IGNORÉ"}


def fr(value, unit=" s"):
    """Nombre au format français (virgule décimale)."""
    return f"{value:.1f}".replace(".", ",") + unit


def link(key):
    return f"[{key}]({JIRA}{key})" if key else "—"


def collect(suite, out):
    for spec in suite.get("specs", []):
        for test in spec["tests"]:
            results = test.get("results", [])
            last = results[-1] if results else {}
            status = {"expected": "PASS", "flaky": "FLAKY", "unexpected": "FAIL",
                      "skipped": "SKIP"}.get(test.get("status"), "FAIL")
            keys = [t for t in spec.get("tags", []) if re.fullmatch(r"SCRUM-\d+", t)]
            error = ""
            if status == "FAIL" and last.get("error"):
                error = ANSI.sub("", last["error"].get("message", "")).strip()
            shot = next((a.get("path") for a in last.get("attachments", [])
                         if a.get("contentType") == "image/png" and a.get("path")), "")
            video = next((a.get("path") for a in last.get("attachments", [])
                          if a.get("contentType", "").startswith("video/") and a.get("path")), "")
            out.append({
                "title": spec["title"],
                "story": keys[0] if len(keys) > 1 else "",
                "test": keys[-1] if keys else "",
                "status": status,
                "tries": len(results),
                "duration": sum(r.get("duration", 0) for r in results) / 1000,
                "project": test.get("projectName", ""),
                "error": error,
                "shot": shot,
                "video": video,
                "last_duration": last.get("duration", 0) / 1000,
            })
    for child in suite.get("suites", []):
        collect(child, out)


def build(plan, lang="fr"):
    data = json.loads(RESULTS.read_text(encoding="utf-8"))
    rows = []
    for suite in data["suites"]:
        collect(suite, rows)
    stats = data.get("stats", {})
    start = datetime.fromisoformat(stats["startTime"].replace("Z", "+00:00")).astimezone()
    total = len(rows)
    count = {k: sum(1 for r in rows if r["status"] == k) for k in ICON}
    passed = count["PASS"] + count["FLAKY"]
    rate = fr(passed / total * 100, " %") if total else "—"
    stories = sorted({r["story"] for r in rows if r["story"]})
    projects = sorted({r["project"] for r in rows if r["project"]})

    lines = [
        f"# Rapport d'exécution automatisée – {start:%d/%m/%Y %H:%M}",
        "",
        "| | |", "|---|---|",
        f"| **Date** | {start:%d/%m/%Y à %H:%M} (heure locale) |",
        f"| **Story / ticket** | {', '.join(link(s) for s in stories) or '—'} |",
        f"| **Test Plan** | {link(plan) if plan else '—'} |",
        f"| **Outil** | Playwright + playwright-bdd (Gherkin des sous-tâches Jira) |",
        f"| **Navigateur(s)** | {', '.join(projects) or '—'} |",
        f"| **Durée totale** | {fr(stats.get('duration', 0) / 1000)} |",
        "",
        "## Résultat global", "",
        "| Total | ✅ Réussis | ⚠️ Instables | ❌ Échoués | ⏭️ Ignorés | Taux de réussite |",
        "|---|---|---|---|---|---|",
        f"| {total} | {count['PASS']} | {count['FLAKY']} | {count['FAIL']} | {count['SKIP']} | **{rate}** |",
        "",
        "## Détail par test", "",
        "| Test Xray | Scénario | Résultat | Essais | Durée |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {link(r['test'])} | {r['title']} | {ICON[r['status']]} | {r['tries']} "
                     f"| {fr(r['duration'])} |")
    failed = [r for r in rows if r["status"] == "FAIL"]
    if failed:
        lines += ["", "## Échecs", ""]
        for r in failed:
            msg = r["error"][:1200] or "(pas de message d'erreur)"
            lines += [f"### {r['test']} – {r['title']}", "", "```", msg, "```",
                      "Preuves (capture, vidéo, trace) : `automation/test-results/`.", ""]
    flaky = [r for r in rows if r["status"] == "FLAKY"]
    if flaky:
        lines += ["", "## Tests instables",
                  "Réussis seulement après relance : " + ", ".join(link(r["test"]) for r in flaky), ""]
    lines += ["", "## Rapport détaillé",
              "Rapport HTML Playwright : `automation/playwright-report/index.html` "
              "(`npm run report` dans le dossier `automation`)."]

    REPORTS.mkdir(exist_ok=True)
    path = REPORTS / f"execution-playwright-{start:%Y-%m-%d-%H%M}.md"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    subject = (f"Rapport d'exécution Playwright {start:%d/%m/%Y %H:%M} – "
               f"{passed}/{total} réussis" + (f" ({count['FAIL']} en échec)" if count["FAIL"] else ""))
    meta = {"start": start, "plan": plan, "stories": stories, "projects": projects,
            "duration": stats.get("duration", 0) / 1000, "rate": rate, "total": total,
            "passed": passed, "count": count}
    html_path = path.with_name(path.stem + ("" if lang == "fr" else f"-{lang}") + ".html")
    html_path.write_text(build_html(rows, meta, lang), encoding="utf-8")
    return path, html_path, rows, subject, {"total": total, "passed": passed, "failed": count["FAIL"],
                                      "flaky": count["FLAKY"], "skipped": count["SKIP"]}


# ---------- Rapport PDF (HTML mis en page puis converti par Chromium) ----------

PILL = {"PASS": ("Réussi", "#E3F2E8", "#1E6B3E"), "FLAKY": ("Instable", "#FDF1DC", "#8A5A00"),
        "FAIL": ("Échec", "#FBE4E1", "#A3271B"), "SKIP": ("Ignoré", "#ECEEF2", "#4A5268")}

CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{font-family:'Segoe UI',Arial,sans-serif;color:#1B2340;font-size:10.5pt;background:#fff}
a{color:inherit;text-decoration:none}
.hero{background:#1B2340;color:#F6F4EF;border-radius:14px;padding:26px 30px;display:flex;
      justify-content:space-between;align-items:center;gap:24px}
.kicker{font-size:8.5pt;letter-spacing:2.5px;text-transform:uppercase;color:#F2A65A;font-weight:600}
h1{font-size:22pt;font-weight:700;margin:6px 0 4px}
.sub{color:#C9CFDD;font-size:10pt}
.verdict{display:inline-block;margin-top:12px;padding:5px 12px;border-radius:999px;font-weight:600;
         font-size:9.5pt}
.donut{flex:none;text-align:center}
.donut .lbl{font-size:8.5pt;color:#C9CFDD;margin-top:4px}
.meta{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin:16px 0}
.meta div{background:#F6F4EF;border-radius:10px;padding:10px 12px}
.meta b{display:block;font-size:7.5pt;text-transform:uppercase;letter-spacing:1.2px;color:#7A8094;
        font-weight:600;margin-bottom:3px}
.kpis{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:20px}
.kpi{border:1px solid #E2DED4;border-radius:10px;padding:12px 14px;border-top:5px solid var(--c)}
.kpi .n{font-size:22pt;font-weight:700;line-height:1;color:var(--c)}
.kpi .t{color:#4A5268;font-size:9pt;margin-top:4px}
h2{font-size:13pt;margin:4px 0 10px;display:flex;align-items:center;gap:8px}
h2:before{content:'';width:6px;height:16px;border-radius:3px;background:#C9541F}
table{width:100%;border-collapse:collapse;margin-bottom:20px}
th{text-align:left;font-size:7.5pt;text-transform:uppercase;letter-spacing:1.2px;color:#7A8094;
   font-weight:600;padding:7px 10px;border-bottom:2px solid #1B2340}
td{padding:8px 10px;border-bottom:1px solid #ECEAE4;vertical-align:middle}
tr:nth-child(even) td{background:#FAF9F6}
td.key{font-weight:600;white-space:nowrap}
td.num{text-align:right;white-space:nowrap;color:#4A5268}
.pill{display:inline-block;padding:3px 10px;border-radius:999px;font-weight:600;font-size:8.5pt;
      white-space:nowrap}
.fail{border:1px solid #F0C9C3;border-left:5px solid #A3271B;border-radius:10px;padding:14px 16px;
      margin-bottom:14px;page-break-inside:avoid}
.fail h3{font-size:11pt;margin-bottom:8px}
.fail pre{background:#1B2340;color:#F6F4EF;border-radius:8px;padding:10px 12px;font-size:8pt;
          white-space:pre-wrap;word-break:break-word;font-family:Consolas,monospace}
.fail img{width:100%;border:1px solid #E2DED4;border-radius:8px;margin-top:10px}
.cap{font-size:8pt;color:#7A8094;margin-top:4px}
.keep{break-inside:avoid;page-break-inside:avoid}
.note{font-size:8.5pt;color:#7A8094;margin-top:6px}
"""


def donut(passed, total):
    """Anneau SVG du taux de réussite."""
    pct = passed / total if total else 0
    r, c = 42, 2 * 3.14159 * 42
    color = "#3FB27F" if pct == 1 else "#F2A65A" if pct >= 0.8 else "#E2614F"
    return (f'<svg width="112" height="112" viewBox="0 0 112 112">'
            f'<circle cx="56" cy="56" r="{r}" fill="none" stroke="#2E3757" stroke-width="12"/>'
            f'<circle cx="56" cy="56" r="{r}" fill="none" stroke="{color}" stroke-width="12" '
            f'stroke-linecap="round" stroke-dasharray="{c * pct:.1f} {c:.1f}" '
            f'transform="rotate(-90 56 56)"/>'
            f'<text x="56" y="62" text-anchor="middle" fill="#F6F4EF" font-size="20" '
            f'font-weight="700" font-family="Segoe UI,Arial">{round(pct * 100)}%</text></svg>')


def short_error(msg):
    """Garde l'essentiel du message d'erreur Playwright (sans le journal d'appels)."""
    keep = []
    for line in msg.splitlines():
        if line.strip().lower().startswith("call log"):
            break
        keep.append(line.rstrip())
    return "\n".join(keep).strip()[:900] or "(pas de message d'erreur)"


def image_uri(path_str):
    path = Path(path_str)
    if not path.exists():
        return ""
    return "data:image/png;base64," + base64.b64encode(path.read_bytes()).decode()


TEXT = {
    "fr": {
        "pill": {"PASS": "Réussi", "FLAKY": "Instable", "FAIL": "Échec", "SKIP": "Ignoré"},
        "ok": "Campagne réussie", "ko": "{n} test(s) en échec",
        "kpis": ("Tests exécutés", "Réussis", "Échecs", "Instables"),
        "kicker": "Testing Factory · Rapport d'exécution", "h1": "Exécution du {d}", "date": "%d/%m/%Y",
        "sub": "Lancée à {t} · Playwright + playwright-bdd · scénarios Gherkin des sous-tâches Jira",
        "rate": "taux de réussite", "meta": ("Story / ticket", "Test Plan", "Navigateur", "Durée totale"),
        "detail": "Détail par test", "th": ("Test Xray", "Scénario", "Résultat", "Essais", "Durée"),
        "fails": "Analyse des échecs", "shot": "Capture d'écran au moment de l'échec",
        "flaky": "Tests instables", "flaky_txt": "Réussis seulement après relance : ",
        "note": "Preuves complètes (vidéo, trace) dans automation/test-results/ · "
                "rapport interactif : npm run report dans le dossier automation.",
        "title": "Rapport d'exécution", "noerr": "(pas de message d'erreur)",
        "footer": "Testing Factory · Rapport d'exécution automatisée",
    },
    "en": {
        "pill": {"PASS": "Passed", "FLAKY": "Flaky", "FAIL": "Failed", "SKIP": "Skipped"},
        "ok": "All tests passed", "ko": "{n} test(s) failed",
        "kpis": ("Tests run", "Passed", "Failed", "Flaky"),
        "kicker": "Testing Factory · Test execution report", "h1": "Test run of {d}", "date": "%d %b %Y",
        "sub": "Started at {t} · Playwright + playwright-bdd · Gherkin scenarios from Jira sub-tasks",
        "rate": "pass rate", "meta": ("Story / ticket", "Test Plan", "Browser", "Total duration"),
        "detail": "Results by test", "th": ("Xray test", "Scenario", "Result", "Attempts", "Duration"),
        "fails": "Failure analysis", "shot": "Screenshot taken at the moment of failure",
        "flaky": "Flaky tests", "flaky_txt": "Passed only after a retry: ",
        "note": "Full evidence (video, trace) in automation/test-results/ · "
                "interactive report: npm run report in the automation folder.",
        "title": "Test execution report", "noerr": "(no error message)",
        "footer": "Testing Factory · Automated test execution report",
    },
}


def num(value, lang, unit=" s"):
    """Number in the report language (decimal comma in French)."""
    return fr(value, unit) if lang == "fr" else f"{value:.1f}{unit}"


def build_html(rows, m, lang="fr"):
    e = html.escape
    T = TEXT[lang]
    count, total = m["count"], m["total"]
    ok = count["FAIL"] == 0
    verdict = (T["ok"], "#3FB27F", "#0F2A1C") if ok else \
              (T["ko"].format(n=count["FAIL"]), "#E2614F", "#2A0F0B")
    jira = lambda k: f'<a href="{JIRA}{k}">{e(k)}</a>' if k else "—"
    kpis = list(zip(T["kpis"], (total, count["PASS"], count["FAIL"], count["FLAKY"]),
                    ("#1B2340", "#1E6B3E", "#A3271B", "#8A5A00")))
    meta = T["meta"]

    body = [
        '<div class="hero"><div>',
        f'<div class="kicker">{e(T["kicker"])}</div>',
        f'<h1>{e(T["h1"].format(d=m["start"].strftime(T["date"])))}</h1>',
        f'<div class="sub">{e(T["sub"].format(t=m["start"].strftime("%H:%M")))}</div>',
        f'<span class="verdict" style="background:{verdict[1]};color:{verdict[2]}">{e(verdict[0])}</span>',
        f'</div><div class="donut">{donut(m["passed"], total)}<div class="lbl">{e(T["rate"])}</div></div></div>',
        '<div class="meta">',
        f'<div><b>{meta[0]}</b>{", ".join(jira(s) for s in m["stories"]) or "—"}</div>',
        f'<div><b>{meta[1]}</b>{jira(m["plan"])}</div>',
        f'<div><b>{meta[2]}</b>{e(", ".join(m["projects"]) or "—")}</div>',
        f'<div><b>{meta[3]}</b>{num(m["duration"], lang)}</div>',
        '</div><div class="kpis">',
    ]
    body += [f'<div class="kpi" style="--c:{c}"><div class="n">{n}</div><div class="t">{e(t)}</div></div>'
             for t, n, c in kpis]
    th = T["th"]
    body += [f'</div><h2>{e(T["detail"])}</h2><table><thead><tr><th>{th[0]}</th><th>{th[1]}</th>'
             f'<th>{th[2]}</th><th style="text-align:right">{th[3]}</th>'
             f'<th style="text-align:right">{th[4]}</th></tr></thead><tbody>']
    for r in rows:
        _, bg, fg = PILL[r["status"]]
        label = T["pill"][r["status"]]
        body.append(f'<tr><td class="key">{jira(r["test"])}</td><td>{e(r["title"])}</td>'
                    f'<td><span class="pill" style="background:{bg};color:{fg}">{label}</span></td>'
                    f'<td class="num">{r["tries"]}</td><td class="num">{num(r["duration"], lang)}</td></tr>')
    body.append('</tbody></table>')

    failed = [r for r in rows if r["status"] == "FAIL"]
    for i, r in enumerate(failed):
        img = image_uri(r["shot"]) if r["shot"] else ""
        # Le titre de section reste collé à la première fiche d'échec.
        body.append('<div class="keep">' + (f'<h2>{e(T["fails"])}</h2>' if i == 0 else '')
                    + f'<div class="fail"><h3>{jira(r["test"])} · {e(r["title"])}</h3>'
                    f'<pre>{e(short_error(r["error"]) if r["error"] else T["noerr"])}</pre>')
        if img:
            body.append(f'<img src="{img}"><div class="cap">{e(T["shot"])}</div>')
        body.append('</div></div>')
    flaky = [r for r in rows if r["status"] == "FLAKY"]
    if flaky:
        body.append(f'<h2>{e(T["flaky"])}</h2><p>{e(T["flaky_txt"])}'
                    + ", ".join(jira(r["test"]) for r in flaky) + '</p>')
    body.append(f'<p class="note">{e(T["note"])}</p>')
    return (f'<!doctype html><html lang="{lang}"><head><meta charset="utf-8">'
            f'<title>{e(T["title"])}</title><style>{CSS}</style></head><body>'
            + "".join(body) + '</body></html>')


# ---------- Vidéo résumé de 10 s (montage des vidéos Playwright) ----------

VIDEO_SECONDS = 10
FONT = "C\\:/Windows/Fonts/segoeuib.ttf"
BADGE = {"PASS": ("REUSSI", "0x2E9E62"), "FLAKY": ("INSTABLE", "0xD08A10"),
         "FAIL": ("ECHEC", "0xC0392B"), "SKIP": ("IGNORE", "0x6B7280")}


def make_video(rows, target):
    """Monte les vidéos des tests en un MP4 de 10 s : chaque test a la même part de temps,
    accélérée, avec un bandeau « clé Xray · scénario » et le résultat. Renvoie le chemin
    ou None si aucune vidéo n'est disponible."""
    clips = [r for r in rows if r["video"] and Path(r["video"]).exists()]
    if not clips:
        return None
    import imageio_ffmpeg  # ffmpeg complet (pip install imageio-ffmpeg)
    seg = VIDEO_SECONDS / len(clips)
    work = target.parent / ".video-tmp"
    work.mkdir(exist_ok=True)
    cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-hide_banner", "-loglevel", "error"]
    parts = []
    for i, r in enumerate(clips):
        cmd += ["-i", str(Path(r["video"]).resolve())]
        label = f"{r['test']}  ·  {r['title']}"
        (work / f"l{i}.txt").write_text(label[:70], encoding="utf-8")
        badge, color = BADGE[r["status"]]
        # On saute la page blanche du démarrage (chargement initial du navigateur).
        skip = min(1.2, r["last_duration"] * 0.3)
        speed = seg / max(r["last_duration"] - skip, seg)  # < 1 : accéléré
        parts.append(
            f"[{i}:v]trim=start={skip:.2f},setpts=PTS-STARTPTS,"
            f"setpts=PTS*{speed:.4f},fps=25,scale=960:540,"
            f"tpad=stop_mode=clone:stop_duration={seg:.3f},trim=duration={seg:.3f},setpts=PTS-STARTPTS,"
            f"drawbox=x=0:y=ih-46:w=iw:h=46:color=0x1B2340@0.92:t=fill,"
            f"drawtext=fontfile='{FONT}':textfile='.video-tmp/l{i}.txt':x=16:y=h-33:"
            f"fontsize=20:fontcolor=white,"
            f"drawbox=x=iw-128:y=ih-38:w=112:h=30:color={color}:t=fill,"
            f"drawtext=fontfile='{FONT}':text='{badge}':x=w-72-text_w/2:y=h-31:"
            f"fontsize=17:fontcolor=white[v{i}]")
    graph = ";".join(parts) + ";" + "".join(f"[v{i}]" for i in range(len(clips))) \
        + f"concat=n={len(clips)}:v=1:a=0[out]"
    (work / "graph.txt").write_text(graph, encoding="utf-8")
    cmd += ["-filter_complex_script", ".video-tmp/graph.txt", "-map", "[out]", "-an",
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "26", "-pix_fmt", "yuv420p",
            "-movflags", "+faststart", target.name]
    proc = subprocess.run(cmd, cwd=target.parent, capture_output=True, text=True, encoding="utf-8")
    for f in work.iterdir():
        f.unlink()
    work.rmdir()
    if proc.returncode != 0 or not target.exists():
        raise RuntimeError("montage vidéo impossible : " + proc.stderr.strip()[-400:])
    return target


def to_pdf(html_path, lang="fr"):
    """Convertit le HTML en PDF avec le Chromium de Playwright (dossier automation)."""
    pdf = html_path.with_suffix(".pdf")
    proc = subprocess.run(["node", "scripts/render-pdf.mjs", str(html_path), str(pdf), TEXT[lang]["footer"]],
                          cwd=ROOT / "automation", capture_output=True, text=True,
                          encoding="utf-8", shell=(sys.platform == "win32"))
    if proc.returncode != 0 or not pdf.exists():
        raise RuntimeError("conversion PDF impossible : " + (proc.stderr or proc.stdout).strip()[-400:])
    html_path.unlink()
    return pdf


def run(script, *args):
    proc = subprocess.run([sys.executable, str(HERE / script), *args],
                          capture_output=True, text=True, encoding="utf-8")
    try:
        return json.loads(proc.stdout.strip())
    except json.JSONDecodeError:
        return {"ok": False, "error": (proc.stdout or proc.stderr).strip()[-500:]}


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    args = sys.argv[1:]
    plan = args[args.index("--plan") + 1] if "--plan" in args else ""
    if not RESULTS.exists():
        print(json.dumps({"ok": False, "error": f"{RESULTS} introuvable : lance d'abord les tests"}, ensure_ascii=False))
        sys.exit(1)
    lang = args[args.index("--lang") + 1] if "--lang" in args else "fr"
    path, html_path, rows, subject, counts = build(plan, lang)
    pdf = to_pdf(html_path, lang)
    out = {"ok": True, "rapport": str(path.relative_to(ROOT)), "pdf": str(pdf.relative_to(ROOT)),
           "sujet": subject, **counts}
    video = None
    if "--no-video" not in args:
        try:
            video = make_video(rows, path.with_suffix(".mp4"))
            out["video"] = str(video.relative_to(ROOT)) if video else "aucune vidéo de test"
        except Exception as exc:  # le rapport part quand même sans vidéo
            out["video"] = f"échec : {exc}"
    if "--no-send" not in args:
        summary = (f"{subject}\n{counts['passed']}/{counts['total']} réussis · "
                   f"{counts['failed']} échec(s) · {counts['flaky']} instable(s)\n"
                   "Rapport détaillé en PDF ci-joint"
                   + (" + vidéo résumé de 10 s." if video else "."))
        extra = [str(video)] if video else []
        out["email"] = run("mailer.py", "send-doc", str(pdf), subject, summary, *extra)
        out["slack"] = run("slack.py", "send-doc", str(pdf), summary, *extra)
        out["teams"] = run("teams.py", "send-doc", str(pdf), summary)
        out["ok"] = any(out[c].get("ok") and not out[c].get("skipped")
                        for c in ("email", "slack", "teams"))
    print(json.dumps(out, ensure_ascii=False, indent=2))
    sys.exit(0 if out["ok"] else 1)


if __name__ == "__main__":
    main()
