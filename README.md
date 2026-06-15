# Job Search Assistant

A configurable, automated job scanner that runs entirely on GitHub Actions — no server, no local setup required.

Fetches listings from Indeed, LinkedIn, and (optionally) USAJobs, scores them against your criteria using Claude AI, and emails you a ranked HTML report. Works for any field and any location.

## How it works

1. GitHub Actions runs on your schedule (default: weekdays at 9 AM ET)
2. The scanner fetches jobs matching your search queries
3. Each new listing is scored against your criteria using Claude AI (or free keyword fallback)
4. Results are ranked into Tier A / B / C and emailed as a styled HTML report
5. Seen jobs are tracked so you only receive new listings each run

## Setup

### 1. Fork this repo

Click **Fork** at the top right. Your fork is where your personal config lives.

### 2. Create your config

In your fork, copy `config.example.yaml` to `config.yaml` and fill it in:

- Your job search queries and target locations
- Location include/exclude rules (or leave `include` empty to accept everywhere)
- A scoring prompt — describe in plain English what a great job looks like for you
- Your resume file name(s) — shown in output so you know what to send

Commit `config.yaml` to your fork. The Actions workflow reads it from the repo at run time.

### 3. Add GitHub Secrets

Go to your fork → **Settings → Secrets and variables → Actions** → **New repository secret**:

| Secret | Required | Purpose |
|--------|----------|---------|
| `NOTIFY_EMAIL` | Yes | Where to send the results email |
| `GMAIL_USERNAME` | Yes | Gmail address used to send the email |
| `GMAIL_APP_PASSWORD` | Yes | [Gmail App Password](https://myaccount.google.com/apppasswords) — not your login password |
| `ANTHROPIC_API_KEY` | No | Enables Claude AI scoring. Without it, uses free keyword scoring. |
| `USAJOBS_API_KEY` | No | Enables USAJobs (US federal jobs). [Get a free key](https://developer.usajobs.gov/APIRequest/Index). |
| `SLACK_WEBHOOK_URL` | No | Enables a Slack summary after each scan. |

### 4. Enable Actions

Go to your fork → **Actions** tab → enable workflows if prompted.

That's it. The scanner runs on schedule automatically. You can also trigger it manually from the **Actions** tab at any time.

---

## Adjusting the schedule

Edit the `cron` line in `.github/workflows/scan.yml`:

```yaml
- cron: '0 13 * * 1-5'    # UTC — 9 AM ET on weekdays
```

Use [crontab.guru](https://crontab.guru) to build any schedule you want.

---

## Scoring

**With Claude** (`ANTHROPIC_API_KEY` set): each job is evaluated against the `scoring.prompt` in your `config.yaml`. Claude returns a tier, score (1–10), and a one-line reason. Claude Haiku costs roughly **$0.02–0.05 per run** for ~100 jobs.

**Without an API key (free)**: falls back to keyword scoring using your `boost_keywords` list. Less nuanced, but zero cost.

Tier meaning:

| Tier | Meaning |
|------|---------|
| A | Strong match — apply this week |
| B | Decent fit — apply next week |
| C | Backup — apply if nothing better |

---

## Tracking applications

```bash
python apply.py          # show your full pipeline
python apply.py add      # log a new application
python apply.py update   # update status on an existing one
```

Applications are stored in `applications.csv`. Commit it to your fork to keep your history backed up.

---

## Files

| File | Purpose |
|------|---------|
| `config.example.yaml` | Template — copy to `config.yaml` to get started |
| `config.yaml` | Your personal config (committed to your fork) |
| `scanner.py` | The scanning and scoring engine |
| `apply.py` | Application tracker CLI |
| `seen_jobs.csv` | Dedup store — committed automatically by Actions after each run |
| `applications.csv` | Your logged applications |
