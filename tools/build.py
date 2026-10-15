#!/usr/bin/env python3
"""Build the password-protected, read-only copy of Ethan's Hub for GitHub Pages.

Usage:
  python3 tools/build.py --data DIR [--strava strava.json] --out index.html
  (the password comes from the STATICRYPT_PASSWORD environment variable)

DIR holds the hub's database documents as JSON files named <doc>.json
(calendar, school, vb, fit, about, home, daily, resume, trips, week), either as
the raw document body or wrapped as {"data": {...}}.
strava.json is {"acts": [...list_activities items...], "sets": {activityId: [...]}}.

Before anything is written, personal details are removed: grades, phone
number, team travel logistics (departure times, flights, hotels, uniforms),
booking confirmation numbers and uploaded photos.
"""
import argparse, datetime, json, os, re, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = ["calendar", "school", "vb", "fit", "about", "home", "daily", "resume", "trips", "week", "plan"]
LOGI = re.compile(r"\b(CGR|CPRA|LGA|SNA|CMH|flight|hotel|uniform|leave CGR|ETA|W/G|black jacket|fly|flies|departure|depart)\b", re.I)


def load(d, n):
    p = os.path.join(d, n + ".json")
    if not os.path.exists(p):
        return None
    j = json.load(open(p))
    return j.get("data", j) if isinstance(j, dict) and "data" in j and isinstance(j["data"], dict) else j


def scrub_text(t):
    """Drop sentences / clauses that carry team travel logistics."""
    if not t:
        return t
    parts = re.split(r"(?<=[.;])\s+", t)
    keep = [p for p in parts if not LOGI.search(p)]
    return " ".join(keep).strip()


def sanitize(docs):
    s = docs.get("school")
    if s:
        s["grades"] = {}
        for c in s.get("courses", []):
            c.pop("canvasScore", None); c.pop("canvasGrade", None)
    r = docs.get("resume")
    if r:
        r["phone"] = ""
    vb = docs.get("vb")
    if vb:
        for t in vb.get("tournaments", []):
            t["legs"] = []
    cal = docs.get("calendar")
    if cal:
        for e in cal.get("events", []):
            if e.get("cat") == "Volleyball":
                name = e.get("title", "").split(" — ")[0]
                rest = e.get("title", "")[len(name):]
                place = re.search(r"\(([^)]*)\)", rest)
                e["title"] = name + (" — " + place.group(1) if place and not LOGI.search(place.group(1)) else "")
    tr = docs.get("trips")
    if tr:
        for t in tr.get("trips", []):
            for b in t.get("bookings", []):
                b.pop("conf", None)
            t["photos"] = []; t["cover"] = None
    ab = docs.get("about")
    if ab:
        ab["photos"] = []
    wk = docs.get("week")
    if wk:
        for w in wk.get("weeks", []):
            w["headline"] = scrub_text(w.get("headline", ""))
            w["focus"] = [scrub_text(f) for f in w.get("focus", []) if scrub_text(f)]
            for d in w.get("days", []):
                for it in d.get("items", []):
                    if it.get("tag") == "MAV" and LOGI.search(it.get("text", "")):
                        it["text"] = "Team travel"
    dl = docs.get("daily")
    if dl:
        for ed in dl.get("editions", []):
            wx = ed.get("weather") or {}
            wx["callout"] = scrub_text(wx.get("callout", ""))
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--strava")
    ap.add_argument("--out", default=os.path.join(HERE, "..", "index.html"))
    a = ap.parse_args()
    if not os.environ.get("STATICRYPT_PASSWORD"):
        sys.exit("Set STATICRYPT_PASSWORD")
    docs = {n: load(a.data, n) for n in DOCS}
    docs = {k: v for k, v in docs.items() if v is not None}
    docs = sanitize(docs)
    strava = {"acts": [], "sets": {}}
    if a.strava and os.path.exists(a.strava):
        strava = json.load(open(a.strava))
        for x in strava.get("acts", []):
            x.pop("location_summary", None); x.pop("description", None)
    from zoneinfo import ZoneInfo
    now = datetime.datetime.now(ZoneInfo("America/New_York"))
    snap = {"builtAt": now.isoformat(timespec="minutes"), "docs": docs, "strava": strava}
    tpl = open(os.path.join(HERE, "hub-template.html")).read()
    js = json.dumps(snap, ensure_ascii=False).replace("</", "<\\/")
    page = ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">"
            "<meta name=\"robots\" content=\"noindex,nofollow\">"
            "<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}body{margin:0;font:14px system-ui}img{max-width:100%}[hidden]{display:none!important}</style>"
            "</head><body><script>window.__SNAPSHOT=" + js + ";</script>" + tpl + "</body></html>")
    with tempfile.TemporaryDirectory() as td:
        src = os.path.join(td, "index.html")
        open(src, "w").write(page)
        outdir = os.path.join(td, "enc")
        subprocess.run(["npx", "--yes", "staticrypt@3.5.4", src, "-d", outdir, "--short",
                        "-c", "false", "-s", json.load(open(os.path.join(HERE, ".staticrypt.json")))["salt"],
                        "--remember", "30",
                        "--template-title", "Ethan's Hub",
                        "--template-instructions", "Private hub. Enter the password to unlock.",
                        "--template-button", "Unlock",
                        "--template-color-primary", "#E2470F",
                        "--template-color-secondary", "#2B1813",
                        "--template-error", "Wrong password"], check=True, stdout=subprocess.DEVNULL)
        enc = open(os.path.join(outdir, "index.html")).read()
        enc = enc.replace("<head>", "<head><meta name=\"robots\" content=\"noindex,nofollow\">", 1)
        open(a.out, "w").write(enc)
    print("built", a.out, "docs:", ",".join(sorted(docs)), "acts:", len(strava.get("acts", [])))


if __name__ == "__main__":
    main()
