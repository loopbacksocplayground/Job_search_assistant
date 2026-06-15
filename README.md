# Job Search Assistant

Automated job scanner that fetches listings from Indeed, LinkedIn, and (optionally) USAJobs, scores them against your criteria, and delivers a ranked HTML report.

Write your searches and scoring criteria in plain English. The tool doesn't know or care what field you're in — it scores listings against whatever you tell it.

---

## What it does

- **Fetches listings** from Indeed, LinkedIn, and (optionally) USAJobs based on your search queries
- **Filters by location** using your include/exclude rules — supports remote, specific cities, states, or metros
- **Deduplicates** across sources and run-to-run so you only see new listings each time
- **Scores each listing** against your criteria using Claude AI or a free keyword fallback
- **Ranks results** into Tier A / B / C and writes a styled HTML report
- **Emails the report** to you automatically after each scheduled run (GitHub Actions mode)
- **Tracks seen jobs** in `seen_jobs.csv` so nothing resurfaces once dismissed

---

## Scoring

Each listing is evaluated against the `scoring.prompt` you write in `config.yaml`.

| Mode | How it works | Cost |
|------|-------------|------|
| **Claude AI** | Sends each job to Claude with your prompt. Returns a tier, score (1–10), and a one-line reason. | ~$0.02–0.05 per run for ~100 jobs |
| **Keyword fallback** | Scores based on `boost_keywords` in your config. No API key needed. | Free |

**Tiers:**

| Tier | Meaning |
|------|---------|
| **A** | Strong match — apply this week |
| **B** | Decent fit — apply next week |
| **C** | Backup — apply if nothing better comes up |

Score thresholds for each tier are configurable in `config.yaml`.

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

## Getting started

See **[SCANNER_SETUP.md](SCANNER_SETUP.md)** for step-by-step instructions to run locally or on GitHub Actions.

---

## Contributing

Pull requests are welcome. If you add a new job source, scoring mode, or output format, please keep it config-driven so it stays easy for others to use without touching the code.
