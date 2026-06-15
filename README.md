# Job Search Assistant

Automated job scanner that runs on GitHub Actions — no server, no local setup required.

Fork it, fill in one config file, add a few secrets, and get a ranked list of new job listings delivered to your inbox on a schedule. Works for any field, any location.

**What it does:**
- Searches Indeed, LinkedIn, and (optionally) USAJobs using your queries
- Filters results by your location rules — remote, specific cities, or both
- Scores each listing against your criteria using Claude AI or free keyword fallback
- Ranks results into Tier A / B / C and emails you a styled HTML report
- Tracks seen jobs so you only get new listings each run

---

## Prerequisites

- A GitHub account (free)
- A Gmail account to send result emails from
- An [Anthropic API key](https://console.anthropic.com/) *(optional — enables AI scoring; ~$0.02–0.05/run)*

No server. No paid job board subscriptions. No local Python environment needed.

---

## Setup

### 1. Fork this repo

Click **Fork** at the top right. Your fork is where your personal config lives.

### 2. Create your config

In your fork, copy `config.example.yaml` to `config.yaml` and fill it in:

```yaml
profile:
  email: "you@example.com"

searches:
  - query: "senior software engineer"
    location: "remote"
  - query: "backend engineer"
    location: "San Francisco, CA"

location:
  always_include_remote: true
  exclude:
    - "United Kingdom"
    - "India"

scoring:
  prompt: |
    Evaluate this for a senior backend engineer with 8 years Python experience.
    Score highly for remote-first, strong eng culture, distributed systems work.

resumes:
  default: "resume.pdf"
```

Open `config.example.yaml` for the full reference with all available options.

Commit `config.yaml` to your fork — the Actions workflow reads it at run time.

### 3. Add GitHub Secrets

Go to your fork → **Settings → Secrets and variables → Actions → New repository secret**:

| Secret | Required | Purpose |
|--------|----------|---------|
| `NOTIFY_EMAIL` | ✅ | Where to deliver the results email |
| `GMAIL_USERNAME` | ✅ | Gmail address used to send the email |
| `GMAIL_APP_PASSWORD` | ✅ | Gmail App Password *(see note below)* |
| `ANTHROPIC_API_KEY` | Optional | Enables Claude AI scoring |
| `USAJOBS_API_KEY` | Optional | Enables US federal job listings ([free key](https://developer.usajobs.gov/APIRequest/Index)) |
| `SLACK_WEBHOOK_URL` | Optional | Enables a Slack summary after each scan |

> **Gmail App Password:** This is not your regular Gmail password. Go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords), create a new app password, and use that value. You must have 2-Step Verification enabled on your Google account.

### 4. Enable Actions

Go to your fork → **Actions** tab → enable workflows if prompted.

Done. The scanner runs on schedule automatically. You can also trigger it manually from the **Actions** tab any time.

---

## Adjusting the schedule

Edit the `cron` line in `.github/workflows/scan.yml`:

```yaml
- cron: '0 13 * * 1-5'    # UTC — 9 AM ET, Monday–Friday
```

Use [crontab.guru](https://crontab.guru) to generate any schedule you want.

---

## Scoring

| Mode | How it works | Cost |
|------|-------------|------|
| **Claude AI** | Sends each job to Claude with your `scoring.prompt`. Returns a tier, score (1–10), and a one-line reason. | ~$0.02–0.05 per run for ~100 jobs |
| **Keyword fallback** | Scores based on `boost_keywords` in your config. No API key needed. | Free |

**Tiers:**

| Tier | Meaning |
|------|---------|
| **A** | Strong match — apply this week |
| **B** | Decent fit — apply next week |
| **C** | Backup — apply if nothing better comes up |

The score thresholds for each tier are configurable in `config.yaml`.

---

## Tracking applications

```bash
python apply.py          # show your application pipeline
python apply.py add      # log a new application
python apply.py update   # update the status of an existing one
```

Applications are stored in `applications.csv`. Commit it to your fork to keep your history backed up across machines.

---

## Files

| File | Purpose |
|------|---------|
| `config.example.yaml` | Full reference config — copy to `config.yaml` to get started |
| `config.yaml` | Your personal config (committed to your fork, not this repo) |
| `scanner.py` | Scanning, filtering, and scoring engine |
| `apply.py` | Application tracker CLI |
| `seen_jobs.csv` | Dedup store — committed by Actions after each run |
| `applications.csv` | Your logged applications |

---

## Contributing

Pull requests are welcome. If you add a new job source, scoring mode, or output format, please keep it config-driven so it stays easy for others to use without touching the code.
