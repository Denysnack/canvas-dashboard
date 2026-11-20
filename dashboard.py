"""
Canvas "What's Due" dashboard.
Reads CANVAS_TOKEN (and optional HIDE_COURSES) from .env, pulls assignments from your
current classes from 14 days ago to 30 days ahead with due + close dates,
prints them, and opens a clean HTML page in your browser.
Uses only Python's standard library -- nothing to pip install.
"""
import json
import os
import sys
import urllib.request
import urllib.error
import webbrowser
from datetime import datetime, timedelta, timezone
from html import escape

HERE = os.path.dirname(os.path.abspath(__file__))
LOOKBACK_DAYS = 14
LOOKAHEAD_DAYS = 30
DEFAULT_CANVAS_URL = "https://ebnet.instructure.com"
HIDE_COURSES = []  # filled from HIDE_COURSES in .env (comma-separated name bits)


def load_env():
    path = os.path.join(HERE, ".env")
    if not os.path.exists(path):
        sys.exit("No .env file found next to dashboard.py. Copy .env.example to .env and fill it in.")
    env = {}
    with open(path, encoding="utf-8-sig") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, val = line.split("=", 1)
            env[key.strip()] = val.strip().strip('"').strip("'")
    url = (env.get("CANVAS_URL") or DEFAULT_CANVAS_URL).rstrip("/")
    token = env.get("CANVAS_TOKEN", "")
    if not url or "YOURSCHOOL" in url:
        sys.exit("Set CANVAS_URL in .env (e.g. https://yourschool.instructure.com).")
    if not url.startswith("http"):
        url = "https://" + url
    if not token or token == "paste_your_token_here":
        sys.exit("Set CANVAS_TOKEN in .env (paste your new token after the =).")
    global HIDE_COURSES
    HIDE_COURSES = env.get("HIDE_COURSES", "").split(",")
    return url, token


def get_all(url, token):
    """GET a Canvas endpoint, following pagination (Link headers)."""
    results = []
    while url:
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                link = resp.headers.get("Link", "")
        except urllib.error.HTTPError as e:
            if e.code == 401:
                sys.exit("Canvas said 401 Unauthorized: token is wrong or expired. Make a new one and paste it in .env.")
            sys.exit(f"Canvas error {e.code}: {e.reason}")
        except urllib.error.URLError as e:
            sys.exit(f"Couldn't reach Canvas ({e.reason}). Check CANVAS_URL in .env and your internet.")
        results.extend(data if isinstance(data, list) else [data])
        url = None
        for part in link.split(","):
            if 'rel="next"' in part:
                url = part[part.find("<") + 1 : part.find(">")]
    return results


def parse_time(s):
    if not s:
        return None
    return datetime.fromisoformat(s.replace("Z", "+00:00"))


def status_of(a, due, closes, now):
    sub = a.get("submission") or {}
    state = sub.get("workflow_state")
    if sub.get("excused"):
        return "excused"
    if state == "graded":
        return "graded"
    if state in ("submitted", "pending_review") or sub.get("submitted_at"):
        return "submitted"
    if closes and closes < now:
        return "CLOSED"
    if due and due < now:
        return "LATE"
    if due and due - now <= timedelta(hours=48):
        return "DUE SOON"
    if not due and closes and closes - now <= timedelta(hours=48):
        return "DUE SOON"
    return "to do"


def is_current(course, now):
    """Skip last year's classes that Canvas still lists as active."""
    if course.get("access_restricted_by_date") or not course.get("name"):
        return False
    hidden = [h.strip().lower() for h in HIDE_COURSES if h.strip()]
    if any(h in course["name"].lower() for h in hidden):
        return False
    term = course.get("term") or {}
    for key in (course.get("end_at"), term.get("end_at")):
        end = parse_time(key)
        if end:
            return end > now
    created = parse_time(course.get("created_at") or course.get("start_at"))
    if created:
        return now - created < timedelta(days=300)
    return True


def build_rows(courses, assignments_by_course, now):
    lo, hi = now - timedelta(days=LOOKBACK_DAYS), now + timedelta(days=LOOKAHEAD_DAYS)
    rows = []
    for c in courses:
        for a in assignments_by_course.get(c["id"], []):
            if not a.get("published", True):
                continue
            due = parse_time(a.get("due_at"))
            closes = parse_time(a.get("lock_at"))
            key = due or closes
            if not key or not (lo <= key <= hi):
                continue
            rows.append({
                "course": c.get("name", ""),
                "title": a.get("name") or "(untitled)",
                "due": due,
                "closes": closes,
                "status": status_of(a, due, closes, now),
                "points": a.get("points_possible"),
                "link": a.get("html_url") or "",
            })
    rows.sort(key=lambda r: r["due"] or r["closes"])
    return rows


def fmt_due(due):
    if not due:
        return "—"
    return due.astimezone().strftime("%a %b %d, %I:%M %p").replace(" 0", " ")


def print_table(rows):
    print()
    print(f"{'STATUS':<10} {'DUE':<22} {'CLOSES':<22} {'COURSE':<24} ASSIGNMENT")
    print("-" * 110)
    for r in rows:
        print(f"{r['status']:<10} {fmt_due(r['due']):<22} {fmt_due(r['closes']):<22} {r['course'][:23]:<24} {r['title'][:50]}")
    print()


def write_html(rows, now):
    colors = {"LATE": "#e5484d", "CLOSED": "#7c2d2d", "DUE SOON": "#f5a524", "to do": "#8b8d98",
              "submitted": "#30a46c", "graded": "#30a46c", "excused": "#8b8d98"}
    counts = {k: sum(1 for r in rows if r["status"] == k) for k in ("LATE", "DUE SOON", "to do")}
    trs = []
    for r in rows:
        c = colors.get(r["status"], "#8b8d98")
        done = r["status"] in ("submitted", "graded", "excused")
        title = escape(r["title"])
        if r["link"]:
            title = f'<a href="{escape(r["link"])}" target="_blank">{title}</a>'
        pts = "" if r["points"] in (None, 0) else f'{r["points"]:g} pts'
        trs.append(
            f'<tr class="{"done" if done else ""}"><td><span class="pill" style="background:{c}">{escape(r["status"])}</span></td>'
            f'<td>{escape(fmt_due(r["due"]))}</td><td class="muted">{escape(fmt_due(r["closes"]))}</td><td>{escape(r["course"])}</td><td>{title}</td>'
            f'<td class="muted">{pts}</td></tr>'
        )
    html = f"""<!DOCTYPE html><html><head><meta charset="utf-8"><title>What's Due</title>
<style>
body{{font-family:system-ui,Segoe UI,sans-serif;background:#111113;color:#ededef;margin:0;padding:32px}}
h1{{margin:0 0 4px;font-size:28px}} .sub{{color:#8b8d98;margin-bottom:24px}}
.cards{{display:flex;gap:12px;margin-bottom:24px}} .card{{background:#1c1c1f;border-radius:10px;padding:14px 20px;min-width:120px}}
.card b{{font-size:26px;display:block}} table{{width:100%;border-collapse:collapse}}
th,td{{text-align:left;padding:10px 12px;border-bottom:1px solid #26262b;font-size:14px}}
th{{color:#8b8d98;font-weight:500}} a{{color:#ededef}} .muted{{color:#8b8d98}}
.pill{{color:#111;font-weight:600;font-size:12px;padding:3px 8px;border-radius:999px;white-space:nowrap}}
tr.done td{{opacity:.45}}
</style></head><body>
<h1>What's Due</h1><div class="sub">Updated {escape(now.astimezone().strftime("%a %b %d, %I:%M %p"))} &middot; last {LOOKBACK_DAYS} days to next {LOOKAHEAD_DAYS} days</div>
<div class="cards"><div class="card"><b style="color:#e5484d">{counts["LATE"]}</b>late (still open)</div>
<div class="card"><b style="color:#f5a524">{counts["DUE SOON"]}</b>due in 48h</div>
<div class="card"><b>{counts["to do"]}</b>other to do</div></div>
<table><tr><th>Status</th><th>Due</th><th>Closes</th><th>Course</th><th>Assignment</th><th>Points</th></tr>
{"".join(trs) or '<tr><td colspan="6">Nothing found in this window.</td></tr>'}
</table></body></html>"""
    out = os.path.join(HERE, "dashboard.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    return out


def main():
    base_url, token = load_env()
    now = datetime.now(timezone.utc)
    print("Pulling your classes from Canvas...")
    courses = get_all(f"{base_url}/api/v1/courses?enrollment_state=active&include[]=term&per_page=100", token)
    current = [c for c in courses if is_current(c, now)]
    skipped = [c.get("name") for c in courses if c not in current and c.get("name")]
    print("Using:   " + ", ".join(c["name"] for c in current))
    if skipped:
        print("Skipped: " + ", ".join(skipped))
    by_course = {}
    for c in current:
        print(f"  ...{c['name']}")
        by_course[c["id"]] = get_all(
            f"{base_url}/api/v1/courses/{c['id']}/assignments?include[]=submission&per_page=100", token)
    rows = build_rows(current, by_course, now)
    print_table(rows)
    out = write_html(rows, now)
    print(f"Dashboard saved to {out}")
    webbrowser.open("file:///" + out.replace("\\", "/"))


if __name__ == "__main__":
    main()
