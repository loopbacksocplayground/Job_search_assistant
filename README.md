# Job Search Assistant

Automated job scanner that fetches listings from Indeed, LinkedIn, and (optionally) USAJobs, scores them against your criteria, and delivers a ranked HTML report.

Write your searches and scoring criteria in plain English. The tool doesn't know or care what field you're in — it scores listings against whatever you tell it.

**What it does:**
- Searches Indeed, LinkedIn, and (optionally) USAJobs using your queries
- Filters results by your location rules — remote, specific cities, or both
- Scores each listing against your criteria using Claude AI or free keyword fallback
- Ranks results into Tier A / B / C and outputs a styled HTML report
- Tracks seen jobs so you only get new listings each run

---

## Setup — Option A: Run Locally

**Prerequisites:** Python 3.10+

**1. Clone this repo (or your fork):**

```bash
git clone https://github.com/loopbacksocplayground/Job_search_assistant.git
cd Job_search_assistant
```

**2. Install dependencies:**

```bash
pip install -r requirements.txt
```

**3. Create your config:**

```bash
cp config.example.yaml config.yaml   # macOS / Linux
copy config.example.yaml config.yaml  # Windows
```

Open `config.yaml` and fill in your searches, location rules, and scoring prompt. See `config.example.yaml` for the full reference with all available options.

**4. (Optional) Set your API keys as environment variables:**

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=your-key-here
export USAJOBS_API_KEY=your-key-here     # only if usajobs: true in config

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "your-key-here"
$env:USAJOBS_API_KEY   = "your-key-here"
```

Without `ANTHROPIC_API_KEY`, the scanner falls back to free keyword scoring using your `boost_keywords` list.

**5. Run the scanner:**

```bash
python scanner.py
```

Results are written to `job_leads.html` and `job_leads.md` in the project folder. Open `job_leads.html` in a browser to review your leads.

**6. Track your applications:**

```bash
python apply.py          # show your pipeline
python apply.py add      # log a new application
python apply.py update   # update an existing one
```

---

## Setup — Option B: Run on GitHub Actions (scheduled + emailed results)

**Prerequisites:** A GitHub account and a Gmail account.

**1. Fork this repo:**

Click **Fork** at the top right of this page. Your fork is where your personal config and data live.

**2. Create your config:**

In your fork, copy `config.example.yaml` to `config.yaml`, fill it in, and commit it:

```bash
cp config.example.yaml config.yaml   # macOS / Linux
copy config.example.yaml config.yaml  # Windows

# edit config.yaml, then:
git add config.yaml
git commit -m "add config"
git push
```

Open `config.example.yaml` for the full reference with all available options.

**3. Add GitHub Secrets:**

Go to your fork → **Settings → Secrets and variables → Actions → New repository secret** and add each of the following:

| Secret | Required | Purpose |
|--------|----------|---------|
| `NOTIFY_EMAIL` | ✅ | Email address that receives the results report |
| `GMAIL_USERNAME` | ✅ | Gmail address used to send the report |
| `GMAIL_APP_PASSWORD` | ✅ | Gmail App Password *(see note below)* |
| `ANTHROPIC_API_KEY` | Optional | Enables Claude AI scoring; without it, keyword scoring is used |
| `USAJOBS_API_KEY` | Optional | Enables US federal job listings ([get a free key](https://developer.usajobs.gov/APIRequest/Index)) |
| `SLACK_WEBHOOK_URL` | Optional | Sends a Slack summary after each scan |

> **Gmail App Password:** This is not your regular Gmail password. You must first enable 2-Step Verification on your Google account, then go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and generate a new app password. Use that value here.

**4. Enable Actions:**

Go to your fork → **Actions** tab → click **Enable workflows** if prompted.

**5. (Optional) Adjust the schedule:**

The scanner runs weekdays at 9 AM ET by default. To change it, edit the `cron` line in `.github/workflows/scan.yml`:

```yaml
- cron: '0 13 * * 1-5'    # UTC — 9 AM ET, Monday–Friday
```

Use [crontab.guru](https://crontab.guru) to build any schedule you want.

**6. Trigger your first run:**

Go to your fork → **Actions** → **Job Scan** → **Run workflow**. Check the run log to confirm everything works, then let it run on schedule from there.

After each run, results are emailed to `NOTIFY_EMAIL` as a styled HTML attachment. Seen jobs are committed back to `seen_jobs.csv` automatically so you only receive new listings next time.

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
