# Canvas "What's Due" Dashboard

A small Python tool that pulls my assignments from Canvas (East Brunswick's `ebnet.instructure.com`) through the Canvas REST API and shows everything due across all my classes on one page, sorted by date.

Canvas's built-in to-do list mixes up due dates and close dates and still shows last year's classes. This dashboard fixes both problems.

![status](https://img.shields.io/badge/status-working-30a46c) ![python](https://img.shields.io/badge/python-standard%20library%20only-3776ab)

---

## What it does

- Pulls every assignment from my **current** classes, from 14 days ago to 30 days ahead
- Shows **two dates** per assignment:
  - **Due**: when it counts as late
  - **Closes**: when the submission window shuts ("available until")
- Gives each assignment a status:

| Status | Meaning |
|---|---|
| 🔴 **LATE** | Past due but still open. Turn it in now |
| 🟤 **CLOSED** | Window is shut |
| 🟠 **DUE SOON** | Due in the next 48 hours |
| ⚪ **to do** | Coming up later |
| 🟢 **submitted / graded** | Done (faded out) |

- Prints a table in the terminal **and** opens a clean dark-mode HTML page in the browser
- Every assignment title links straight to its Canvas page
- Automatically skips old classes whose term has ended

---

## Setup

**Needs:** Python 3 ([python.org](https://www.python.org/downloads/), check "Add python.exe to PATH" during install). Nothing to `pip install`.

1. **Get a Canvas token:** Canvas → Account → Settings → *Approved Integrations* → **+ New Access Token**. Copy it right away, because Canvas only shows it once. (Max 30 days at my school.)
2. **Create a `.env` file** in this folder:
   ```
   CANVAS_TOKEN=your_token_here
   ```
   Optional lines:
   ```
   CANVAS_URL=https://otherschool.instructure.com   # defaults to ebnet.instructure.com
   HIDE_COURSES=Algebra 2,Chemistry                 # hide classes by part of their name
   ```
3. **Run it:** double-click `run.bat` (or `python dashboard.py`).

---

## How it works

```
.env (token) ──► dashboard.py ──► Canvas REST API ──► filter + sort ──► terminal table
                                                                    └─► dashboard.html (opens in browser)
```

1. `GET /api/v1/courses?enrollment_state=active&include[]=term`: gets my classes and their terms
2. **Filters out old classes**: keeps a course only if its course or term end date is in the future (or, if there are no dates, it was created within the last ~300 days). Also applies `HIDE_COURSES`.
3. `GET /api/v1/courses/:id/assignments?include[]=submission`: for each current class, gets assignments with `due_at`, `lock_at` (close date), and my submission status
4. Keeps assignments whose due (or close) date falls in the window, works out the status, and sorts by date
5. Writes `dashboard.html` and opens it

Pagination is handled by following Canvas's `Link: rel="next"` headers. Uses only Python's standard library (`urllib`, `json`, `webbrowser`).

### Files

| File | What it is |
|---|---|
| `dashboard.py` | The whole program |
| `run.bat` | Double-click launcher for Windows |
| `.env` | My token (**never shared or committed**) |
| `.gitignore` | Keeps `.env` and the generated HTML out of Git |
| `dashboard.html` | Generated output (rebuilt every run) |

---

## Security

- The Canvas token works like a password: anyone with it can act as me in Canvas.
- It lives **only** in `.env`, which is in `.gitignore`, so it never goes to GitHub.
- The script never prints the token.
- Tokens expire after 30 days. If one ever leaks (screenshot, chat, etc.), **regenerate it** in Canvas right away, which kills the old one.

---

## Troubleshooting

| Message | Fix |
|---|---|
| `401 Unauthorized` | Token is wrong or expired. Make a new one and paste it into `.env` |
| `Set CANVAS_TOKEN in .env` | `.env` is missing, empty, or not saved (check for the unsaved dot in VS Code) |
| `Couldn't reach Canvas` | Check the internet connection or `CANVAS_URL` |
| `Python isn't installed` | Install from python.org with "Add to PATH" checked |
| An old class still shows up | Add part of its name to `HIDE_COURSES` in `.env` |

---

## Build log

- **v1:** Used the Canvas *planner* endpoint. Worked, but showed only one date per item (so AP Calc showed the close date instead of the real due date) and included last year's classes.
- **v2:** Switched to the per-course *assignments* endpoint to get both `due_at` and `lock_at`, added LATE vs CLOSED statuses, filtered out ended terms, and added `HIDE_COURSES`.

## Ideas for next versions

- [ ] Run automatically every morning with Windows Task Scheduler
- [ ] Show grades / recent feedback
- [ ] Phone notification for anything due in the next 24 hours
- [ ] Turn it into a web app other students can use with their own tokens
