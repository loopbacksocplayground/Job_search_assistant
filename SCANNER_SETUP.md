# Scanner Setup

Two ways to run Job Search Assistant: locally on your machine, or automatically on a schedule via GitHub Actions.

---

## Option A — Run Locally

**Prerequisites:** Python 3.10+

### 1. Clone this repo (or your fork)

```bash
git clone https://github.com/loopbacksocplayground/job_search_assistant.git
cd Job_search_assistant
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Create your config

```bash
cp config.example.yaml config.yaml   # macOS / Linux
copy config.example.yaml config.yaml  # Windows
```

Open `config.yaml` and fill in:
- Your search queries and target locations
- Location include/exclude rules
- Your scoring prompt — describe in plain English what a strong match looks like
- Your resume file name(s)

See `config.example.yaml` for the full reference with every available option.

### 4. Set your API keys (optional)

Without `ANTHROPIC_API_KEY` the scanner uses free keyword scoring. Without `USAJOBS_API_KEY` it skips USAJobs (only needed if `usajobs: true` in config).

```bash
# macOS / Linux
export ANTHROPIC_API_KEY=your-key-here
export USAJOBS_API_KEY=your-key-here

# Windows (PowerShell)
$env:ANTHROPIC_API_KEY = "your-key-here"
$env:USAJOBS_API_KEY   = "your-key-here"
```

### 5. Run the scanner

```bash
python scanner.py
```

Results are written to `job_leads.html` and `job_leads.md` in the project folder. Open `job_leads.html` in a browser to review your leads.

### 6. Track your applications

```bash
python apply.py          # show your pipeline
python apply.py add      # log a new application
python apply.py update   # update an existing one
```

Applications are saved to `applications.csv`.

---

## Option B — Run on GitHub Actions (scheduled, results emailed)

**Prerequisites:** A GitHub account and a Gmail account.

### 1. Fork this repo

Click **Fork** at the top right of the repo page. Your fork is where your personal config and data live.

### 2. Create your config

In your fork, copy `config.example.yaml` to `config.yaml`, fill it in, and commit it:

```bash
cp config.example.yaml config.yaml   # macOS / Linux
copy config.example.yaml config.yaml  # Windows
```

Edit `config.yaml`, then commit:

```bash
git add config.yaml
git commit -m "add config"
git push
```

See `config.example.yaml` for the full reference with every available option.

### 3. Add GitHub Secrets

Go to your fork → **Settings → Secrets and variables → Actions → New repository secret** and add each of the following:

| Secret | Required | Purpose |
|--------|----------|---------|
| `NOTIFY_EMAIL` | ✅ | Email address that receives the results report |
| `GMAIL_USERNAME` | ✅ | Gmail address used to send the report |
| `GMAIL_APP_PASSWORD` | ✅ | Gmail App Password *(see note below)* |
| `ANTHROPIC_API_KEY` | Optional | Enables Claude AI scoring; without it, keyword scoring is used |
| `USAJOBS_API_KEY` | Optional | Enables US federal job listings ([get a free key](https://developer.usajobs.gov/APIRequest/Index)) |
| `SLACK_WEBHOOK_URL` | Optional | Sends a Slack summary after each scan |

> **Gmail App Password:** This is not your regular Gmail password. You must first enable 2-Step Verification on your Google account, then go to [myaccount.google.com/apppasswords](https://myaccount.google.com/apppasswords) and generate a new app password. Use that value here — not your login password.

### 4. Enable Actions

Go to your fork → **Actions** tab → click **Enable workflows** if prompted.

### 5. Adjust the schedule (optional)

The scanner runs weekdays at 9 AM ET by default. To change it, edit the `cron` line in `.github/workflows/scan.yml`:

```yaml
- cron: '0 13 * * 1-5'    # UTC — 9 AM ET, Monday–Friday
```

Use [crontab.guru](https://crontab.guru) to build any schedule you want.

### 6. Trigger your first run

Go to your fork → **Actions** → **Job Scan** → **Run workflow**.

Check the run log to confirm everything works. After each run, results are emailed to `NOTIFY_EMAIL` as a styled HTML attachment and `seen_jobs.csv` is committed back to the repo automatically.

---

## Troubleshooting

**No results from Indeed or LinkedIn**
jobspy rotates headers automatically, but LinkedIn rate-limits aggressively. If you consistently get 0 results, wait 10–15 minutes and try again. You can also lower `results_per_query` in `config.yaml`.

**USAJobs returns 401**
Your `USAJOBS_API_KEY` is missing or incorrect. Register for a free key at [developer.usajobs.gov](https://developer.usajobs.gov/APIRequest/Index).

**Claude scoring fails**
The scanner automatically falls back to keyword scoring if Claude returns an error. Check that `ANTHROPIC_API_KEY` is set correctly.

**Email not delivered**
Confirm `GMAIL_APP_PASSWORD` is an App Password (not your login password) and that 2-Step Verification is enabled on the sending Gmail account.
