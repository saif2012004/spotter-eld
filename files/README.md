# Spotter ELD Assessment — Claude CLI Prompts

Seven sequential prompts for building the Spotter AI full-stack assessment with Claude Code.

## Setup (do this first)

```bash
mkdir spotter-eld
cd spotter-eld
git init
claude
```

Then feed prompts one at a time. Two equally-good ways:

### Option A — paste from file

Open `prompt-N-*.md` in any editor, copy the contents, paste into Claude Code.

### Option B — pipe directly

```bash
cat ~/path/to/prompt-1-scaffold.md | claude
```

(Or however your claude CLI accepts piped input — check `claude --help`. On most setups, just paste is easier.)

## Order

Run in this order. Don't skip. Don't combine. Wait for each to finish before the next.

1. `prompt-1-scaffold.md` — directory structure, dependencies, no logic yet
2. `prompt-2-hos-simulator.md` — the FMCSA Hours-of-Service engine + tests
3. `prompt-3-geocoding-routing.md` — Nominatim and OSRM wrappers
4. `prompt-4-django-endpoint.md` — `/api/plan-trip/` ties it all together
5. `prompt-5-react-frontend.md` — form, map, summary (no log sheet yet)
6. `prompt-6-log-sheet.md` — the SVG daily log sheet (visually impressive part)
7. `prompt-7-deployment-polish.md` — Render + Vercel configs, README

## After each prompt

1. Read what Claude Code did. Skim the new files.
2. Run the sanity check the prompt tells you to run (usually `manage.py check`, `manage.py test`, or `npm run dev`).
3. If it passed, move to the next prompt.
4. If it failed, paste the error into Claude Code and let it fix it before moving on.

## If Claude Code goes off the rails

Paste this recovery prompt:

```
Stop. Show me what files exist now (tree -L 3) and a 5-line summary of each. Then I'll redirect.
```

That snaps it back to a known state without losing work.

## After all 7 prompts are done

1. **Deploy backend**: push to GitHub → Render → new Web Service → root dir `backend/` → env vars `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS=*.onrender.com`.
2. **Deploy frontend**: Vercel → new project → root dir `frontend/` → env var `VITE_API_URL=<your render url>`.
3. **Smoke-test the live app** with 3 trip scenarios:
   - Short (LA → San Diego, 0 cycle hours) — single log sheet
   - Multi-day (LA → NYC, 0 cycle hours) — 3-4 log sheets, 10-hour resets
   - Near limit (LA → Dallas, 65 cycle hours) — should trigger 34-hour restart
4. **Record Loom** (~4 min): problem statement → live demo → code walkthrough (hos.py + DailyLogSheet.jsx) → deployment links.
5. **Submit** GitHub + Vercel + Loom links in Teamtailor.

## Tips

- **Don't deploy Django to Vercel.** Their serverless Python is finicky with Django. Render's free tier is smoother.
- **Write the tests.** Prompt 2 produces them. Show one passing in the Loom — it tells the evaluator you take HOS accuracy seriously.
- **The log sheet matters most for UI grade.** Spend extra time on Prompt 6 if anything.
- **First Render deploy takes ~5 min.** Don't panic.
- **Render free tier sleeps after 15 min idle** — first request after sleep takes ~30s. Mention this in your Loom or hit the URL right before recording.
