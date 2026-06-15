#!/usr/bin/env python3
"""
Job Search Assistant — scanner.py
Fetches listings from Indeed, LinkedIn, and USAJobs, deduplicates, filters by
your location preferences, and scores with Claude AI or free keyword fallback.
Configure everything in config.yaml.
"""

import csv
import hashlib
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path
import os

import requests
import yaml
from jobspy import scrape_jobs

try:
    import anthropic as _anthropic
    _ANTHROPIC_AVAILABLE = True
except ImportError:
    _ANTHROPIC_AVAILABLE = False

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ── Config ─────────────────────────────────────────────────────────────────────

def load_config() -> dict:
    path = Path("config.yaml")
    if not path.exists():
        sys.exit("config.yaml not found. Copy config.example.yaml → config.yaml and fill it in.")
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f) or {}

CFG = load_config()

_profile  = CFG.get("profile")    or {}
_sources  = CFG.get("sources")    or {}
_location = CFG.get("location")   or {}
_scoring  = CFG.get("scoring")    or {}
_resumes  = CFG.get("resumes")    or {"default": "resume.pdf"}

YOUR_EMAIL     = _profile.get("email", "")
JOB_SEARCHES   = [(s.get("query", ""), s.get("location", "remote"))
                   for s in (CFG.get("searches") or [])]
RESUME_FILES   = _resumes
BOOST_KEYWORDS = [kw.lower() for kw in (_scoring.get("boost_keywords") or [])]
TIER_A_MIN     = int(_scoring.get("tier_a_min_score", 8))
TIER_B_MIN     = int(_scoring.get("tier_b_min_score", 6))
ALWAYS_REMOTE  = bool(_location.get("always_include_remote", True))
INCLUDE_LOCS   = [s.lower() for s in (_location.get("include")  or [])]
EXCLUDE_LOCS   = [s.lower() for s in (_location.get("exclude")  or [])]
SCORING_PROMPT = (_scoring.get("prompt") or "").strip()
USE_INDEED     = bool(_sources.get("indeed",           True))
USE_LINKEDIN   = bool(_sources.get("linkedin",         True))
USE_USAJOBS    = bool(_sources.get("usajobs",          False))
COUNTRY_INDEED = str(_sources.get("country",           "USA"))
RESULTS_WANTED = int(_sources.get("results_per_query", 25))
DAYS_OLD       = int(_sources.get("days_old",          14))
CLAUDE_MODEL   = _scoring.get("model", "claude-haiku-4-5")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
USAJOBS_API_KEY   = os.environ.get("USAJOBS_API_KEY",   "")
SLACK_WEBHOOK_URL = os.environ.get("SLACK_WEBHOOK_URL", "")

SEEN_JOBS_FILE    = Path("seen_jobs.csv")
LEADS_FILE        = Path("job_leads.md")
LEADS_HTML_FILE   = Path("job_leads.html")
SUMMARY_FILE      = Path("_scan_summary.json")
APPLICATIONS_FILE = Path("applications.csv")

TIER_LABEL  = {"A": "Apply this week", "B": "Apply next week", "C": "Backup"}
_TIER_COLOR = {"A": "#1a7f37", "B": "#9a6700", "C": "#57606a"}
_TIER_BG    = {"A": "#dafbe1", "B": "#fff8c5", "C": "#f6f8fa"}

# ── Dedup store ────────────────────────────────────────────────────────────────

def make_id(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()[:12]

def load_seen() -> set:
    if not SEEN_JOBS_FILE.exists():
        return set()
    with open(SEEN_JOBS_FILE, newline="", encoding="utf-8") as f:
        return {row["id"] for row in csv.DictReader(f)}

def append_seen(job: dict):
    exists = SEEN_JOBS_FILE.exists()
    with open(SEEN_JOBS_FILE, "a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["id", "title", "company", "url", "date_seen"])
        if not exists:
            w.writeheader()
        w.writerow({
            "id":        job["id"],
            "title":     job["title"],
            "company":   job["company"],
            "url":       job["url"],
            "date_seen": datetime.now().strftime("%Y-%m-%d"),
        })

def init_applications_csv():
    if not APPLICATIONS_FILE.exists():
        with open(APPLICATIONS_FILE, "w", newline="", encoding="utf-8") as f:
            csv.DictWriter(f, fieldnames=[
                "date_applied", "title", "company", "url", "source",
                "resume", "cover_letter", "status", "follow_up_date", "notes",
            ]).writeheader()

# ── Location filtering ─────────────────────────────────────────────────────────

def passes_location(job: dict) -> bool:
    loc = (job.get("location") or "").lower()

    if ALWAYS_REMOTE and "remote" in loc:
        return True

    # Exclusions take priority
    if any(excl in loc for excl in EXCLUDE_LOCS):
        return False

    # No include list = accept everything not excluded
    if not INCLUDE_LOCS:
        return True

    return any(incl in loc for incl in INCLUDE_LOCS)

def detect_work_type(job: dict) -> str:
    loc  = (job.get("location")    or "").lower()
    desc = (job.get("description") or "").lower()
    if "remote" in loc:
        return "Remote"
    if "hybrid" in loc or "hybrid" in desc:
        return "Hybrid"
    return "On-site"

# ── Resume helpers ─────────────────────────────────────────────────────────────

def default_resume() -> str:
    return next(iter(RESUME_FILES.values()), "resume.pdf")

def resolve_resume(key: str) -> str:
    return RESUME_FILES.get(key, default_resume())

# ── Fetching ───────────────────────────────────────────────────────────────────

def fetch_jobs() -> list[dict]:
    sites = [s for s, on in [("indeed", USE_INDEED), ("linkedin", USE_LINKEDIN)] if on]
    if not sites:
        print("  No job board sources enabled.")
        return []

    jobs = []
    for query, location in JOB_SEARCHES:
        print(f"  Searching: '{query}' / {location} ...")
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=query,
                location=location,
                results_wanted=RESULTS_WANTED,
                hours_old=DAYS_OLD * 24,
                country_indeed=COUNTRY_INDEED,
                linkedin_fetch_description=True,
            )
            for _, row in df.iterrows():
                link = str(row.get("job_url") or "")
                if not link or link.lower() == "nan":
                    continue
                title   = str(row.get("title")       or "").strip()
                company = str(row.get("company")      or "Unknown").strip()
                desc    = str(row.get("description")  or "").strip()
                loc     = str(row.get("location")     or location).strip()
                source  = str(row.get("site")         or "").strip().title()
                if not title or source.lower() == "nan":
                    continue
                jobs.append({
                    "id":          make_id(link),
                    "title":       title,
                    "company":     company,
                    "url":         link,
                    "description": desc,
                    "location":    loc,
                    "source":      source,
                })
            print(f"    {len(df) if df is not None else 0} results")
            time.sleep(3)
        except Exception as e:
            print(f"    [error] {query} / {location}: {e}")
    return jobs

def fetch_usajobs() -> list[dict]:
    if not USAJOBS_API_KEY:
        print("  [usajobs] skipped — USAJOBS_API_KEY secret not set")
        return []
    if not YOUR_EMAIL:
        print("  [usajobs] skipped — profile.email not set in config.yaml")
        return []
    jobs = []
    headers = {
        "User-Agent":        YOUR_EMAIL,
        "Authorization-Key": USAJOBS_API_KEY,
        "Host":              "data.usajobs.gov",
    }
    for query, _ in JOB_SEARCHES:
        try:
            r = requests.get(
                "https://data.usajobs.gov/api/search",
                params={"Keyword": query, "ResultsPerPage": RESULTS_WANTED},
                headers=headers,
                timeout=15,
            )
            r.raise_for_status()
            for item in r.json().get("SearchResult", {}).get("SearchResultItems", []):
                pos  = item["MatchedObjectDescriptor"]
                link = pos.get("PositionURI", "")
                if not link:
                    continue
                details = pos.get("UserArea", {}).get("Details", {})
                jobs.append({
                    "id":          make_id(link),
                    "title":       pos.get("PositionTitle", ""),
                    "company":     pos.get("OrganizationName", ""),
                    "url":         link,
                    "description": details.get("JobSummary", ""),
                    "location":    "Federal / Remote",
                    "source":      "USAJobs",
                })
            time.sleep(1)
        except Exception as e:
            print(f"  [usajobs] {query}: {e}")
    return jobs

# ── Scoring ────────────────────────────────────────────────────────────────────

def _build_prompt(job: dict) -> str:
    snippet      = (job.get("description") or "")[:2500]
    resume_keys  = list(RESUME_FILES.keys())
    default_key  = resume_keys[0] if resume_keys else "default"

    resume_instruction = ""
    resume_json_field  = ""
    if len(resume_keys) > 1:
        resume_instruction = (
            f"Pick the best resume variant from this list: {resume_keys}. "
            f"Include it as the 'resume' key in your JSON.\n\n"
        )
        resume_json_field = f', "resume": "{default_key}"'

    json_template = '{"tier": "A", "score": 8, "reason": "one sentence"' + resume_json_field + "}"

    return (
        f"Title: {job['title']}\n"
        f"Company: {job['company']}\n"
        f"Location: {job['location']}\n"
        f"Description:\n{snippet}\n\n"
        f"{SCORING_PROMPT}\n\n"
        f"{resume_instruction}"
        f"Respond ONLY with valid JSON: {json_template}\n"
        f"Tier A = strong match (score >= {TIER_A_MIN}). "
        f"B = decent (score >= {TIER_B_MIN}). C = backup. score = integer 1-10."
    )

def score_claude(job: dict) -> dict:
    try:
        client   = _anthropic.Anthropic()
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=256,
            system="Respond only with valid JSON. No markdown code fences.",
            messages=[{"role": "user", "content": _build_prompt(job)}],
        )
        data  = json.loads(response.content[0].text)
        score = int(data.get("score", 5))
        tier  = "A" if score >= TIER_A_MIN else "B" if score >= TIER_B_MIN else "C"
        return {
            "tier":   tier,
            "score":  score,
            "reason": str(data.get("reason", "")),
            "resume": resolve_resume(str(data.get("resume", "")).strip()),
        }
    except Exception as e:
        print(f"    [claude error] {e} — falling back to keyword scoring")
        return score_keywords(job)

def score_keywords(job: dict) -> dict:
    text  = f"{job['title']} {job.get('description', '')}".lower()
    score = 5 + sum(0.5 for kw in BOOST_KEYWORDS if kw in text)
    score = min(10, round(score))
    tier  = "A" if score >= TIER_A_MIN else "B" if score >= TIER_B_MIN else "C"
    return {
        "tier":   tier,
        "score":  score,
        "reason": "keyword-based score",
        "resume": default_resume(),
    }

# ── Post-score dedup ───────────────────────────────────────────────────────────

def dedup_scored(jobs: list[dict]) -> list[dict]:
    """Collapse same title+company variants, keeping the highest-scoring entry."""
    seen: dict[tuple, dict] = {}
    for j in jobs:
        title_key   = tuple(re.sub(r"[^\w\s]", "", j["title"].lower()).split()[:6])
        company_key = tuple(re.sub(r"[^\w\s]", "", j["company"].lower()).split()[:3])
        key = (title_key, company_key)
        if key not in seen or j["score"] > seen[key]["score"]:
            seen[key] = j
    return list(seen.values())

# ── Output ─────────────────────────────────────────────────────────────────────

def _sort_key(j: dict) -> tuple:
    return ({"A": 0, "B": 1, "C": 2}.get(j["tier"], 2), -j["score"])

def write_leads(jobs: list[dict]):
    now   = datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"# Job Leads — {now}\n\n",
        f"> {len(jobs)} new leads. Review here, then log applications with `python apply.py add`.\n\n",
    ]

    by_work: dict[str, list] = {"Remote": [], "Hybrid": [], "On-site": []}
    for j in jobs:
        by_work[j.get("work_type", "On-site")].append(j)

    for wtype in ["Remote", "Hybrid", "On-site"]:
        wjobs = sorted(by_work[wtype], key=_sort_key)
        if not wjobs:
            continue
        lines.append(f"## {wtype} ({len(wjobs)})\n\n")
        for j in wjobs:
            lines += [
                f"### {j['title']} — {j['company']}\n",
                f"- **Tier {j['tier']} — {TIER_LABEL[j['tier']]}**  |  **Score:** {j['score']}/10"
                f"  |  **Source:** {j['source']}  |  **Location:** {j['location']}\n",
                f"- **Resume:** `{j['resume']}`\n",
                f"- **Why:** {j['reason']}\n",
                f"- **URL:** {j['url']}\n\n",
            ]

    with open(LEADS_FILE, "w", encoding="utf-8") as f:
        f.writelines(lines)

def write_leads_html(jobs: list[dict]):
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    def job_card(j: dict) -> str:
        tier      = j["tier"]
        color     = _TIER_COLOR.get(tier, "#57606a")
        bg        = _TIER_BG.get(tier, "#f6f8fa")
        label     = TIER_LABEL.get(tier, tier)
        score_pct = j["score"] * 10
        return (
            f'<div style="border:1px solid #d0d7de;border-radius:8px;padding:16px 20px;'
            f'margin-bottom:12px;background:#fff;">'
            f'<div style="display:flex;align-items:center;gap:10px;margin-bottom:8px;flex-wrap:wrap;">'
            f'<a href="{j["url"]}" style="font-size:16px;font-weight:600;color:#0969da;text-decoration:none;">{j["title"]}</a>'
            f'<span style="color:#57606a;font-size:14px;">— {j["company"]}</span>'
            f'<span style="margin-left:auto;background:{bg};color:{color};border:1px solid {color};'
            f'border-radius:20px;padding:2px 10px;font-size:12px;font-weight:600;white-space:nowrap;">'
            f'Tier {tier} · {label}</span></div>'
            f'<div style="display:flex;gap:6px;align-items:center;margin-bottom:8px;flex-wrap:wrap;">'
            f'<span style="font-size:13px;color:#57606a;">Score:</span>'
            f'<div style="background:#e0e0e0;border-radius:4px;height:8px;width:80px;overflow:hidden;display:inline-block;vertical-align:middle;">'
            f'<div style="background:{color};height:100%;width:{score_pct}%;"></div></div>'
            f'<span style="font-size:13px;font-weight:600;color:{color};">{j["score"]}/10</span>'
            f'<span style="color:#d0d7de;">|</span>'
            f'<span style="font-size:13px;color:#57606a;">{j["source"]}</span>'
            f'<span style="color:#d0d7de;">|</span>'
            f'<span style="font-size:13px;color:#57606a;">{j["location"]}</span></div>'
            f'<div style="font-size:13px;color:#24292f;margin-bottom:4px;">{j["reason"]}</div>'
            f'<div style="font-size:12px;color:#57606a;margin-top:6px;">Resume: '
            f'<code style="background:#f6f8fa;padding:1px 5px;border-radius:3px;">{j["resume"]}</code>'
            f'</div></div>'
        )

    by_work: dict[str, list] = {"Remote": [], "Hybrid": [], "On-site": []}
    for j in jobs:
        by_work[j.get("work_type", "On-site")].append(j)

    sections = []
    for wtype in ["Remote", "Hybrid", "On-site"]:
        wjobs = sorted(by_work[wtype], key=_sort_key)
        if not wjobs:
            continue
        cards = "\n".join(job_card(j) for j in wjobs)
        sections.append(
            f"<h2 style='color:#24292f;border-bottom:2px solid #e0e0e0;padding-bottom:6px;'>"
            f"{wtype} ({len(wjobs)})</h2>\n{cards}"
        )

    body = "<div style='margin-top:32px;'></div>".join(sections)
    html = (
        f'<!DOCTYPE html><html lang="en"><head>'
        f'<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
        f'<title>Job Leads — {now}</title></head>'
        f'<body style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',sans-serif;'
        f'max-width:860px;margin:0 auto;padding:24px;background:#f6f8fa;color:#24292f;">'
        f'<div style="background:#fff;border:1px solid #d0d7de;border-radius:10px;padding:24px 32px;">'
        f'<h1 style="margin-top:0;color:#24292f;">Job Leads '
        f'<span style="font-size:14px;font-weight:400;color:#57606a;">— {now}</span></h1>'
        f'<p style="color:#57606a;margin-bottom:24px;">{len(jobs)} new leads this run.</p>'
        f'{body}</div></body></html>'
    )

    with open(LEADS_HTML_FILE, "w", encoding="utf-8") as f:
        f.write(html)

def write_summary(jobs: list[dict]) -> dict:
    top = sorted([j for j in jobs if j["tier"] == "A"], key=lambda j: -j["score"])
    summary = {
        "date":   datetime.now().strftime("%Y-%m-%d"),
        "total":  len(jobs),
        "tier_a": [{"title": j["title"], "company": j["company"],
                    "url": j["url"], "score": j["score"]} for j in top],
    }
    with open(SUMMARY_FILE, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    return summary

def post_to_slack(summary: dict):
    if not SLACK_WEBHOOK_URL:
        return
    tier_a = summary["tier_a"]
    lines  = [
        f":mag: *Job Scan — {summary['date']}*",
        f"{summary['total']} new leads | Tier A: {len(tier_a)}",
        "",
    ]
    if tier_a:
        lines.append("*Top Tier A leads:*")
        for j in tier_a[:5]:
            lines.append(f"• <{j['url']}|{j['title']} @ {j['company']}> ({j['score']}/10)")
    lines.append("\n_Full list in your email._")
    try:
        r = requests.post(SLACK_WEBHOOK_URL, json={"text": "\n".join(lines)}, timeout=10)
        r.raise_for_status()
        print("Slack notification sent.")
    except Exception as e:
        print(f"  [slack] {e}")

# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    print(f"=== Job Search Assistant  {datetime.now().strftime('%Y-%m-%d %H:%M')} ===\n")

    init_applications_csv()
    seen = load_seen()
    print(f"Previously seen: {len(seen)} jobs\n")

    print("Fetching jobs...")
    raw = fetch_jobs()
    if USE_USAJOBS:
        print("Fetching USAJobs...")
        raw += fetch_usajobs()
    print(f"  {len(raw)} total raw listings")

    filtered, dropped = [], 0
    for j in raw:
        if passes_location(j):
            filtered.append(j)
        else:
            dropped += 1
    print(f"  {dropped} dropped by location filter")
    print(f"  {len(filtered)} after location filter")

    deduped, seen_this_run = [], set()
    for j in filtered:
        if j["id"] not in seen and j["id"] not in seen_this_run and j["url"]:
            seen_this_run.add(j["id"])
            deduped.append(j)
    print(f"  {len(deduped)} new after dedup\n")

    if not deduped:
        print("No new jobs found. Done.")
        return

    use_claude  = bool(ANTHROPIC_API_KEY and _ANTHROPIC_AVAILABLE)
    scorer_name = f"Claude ({CLAUDE_MODEL})" if use_claude else "keyword fallback (free)"
    print(f"Scoring {len(deduped)} jobs with {scorer_name}...\n")

    scored = []
    for i, job in enumerate(deduped, 1):
        print(f"  [{i:>3}/{len(deduped)}] {job['title'][:55]} @ {job['company'][:20]}")
        result = score_claude(job) if use_claude else score_keywords(job)
        job.update(result)
        job["work_type"] = detect_work_type(job)
        scored.append(job)
        append_seen(job)

    scored = dedup_scored(scored)
    write_leads(scored)
    write_leads_html(scored)

    counts = {t: sum(1 for j in scored if j["tier"] == t) for t in "ABC"}
    print(f"\nLeads written → {LEADS_FILE} + {LEADS_HTML_FILE}")
    print(f"  Tier A={counts['A']}  B={counts['B']}  C={counts['C']}")

    summary = write_summary(scored)
    print(f"Summary → {SUMMARY_FILE}")
    post_to_slack(summary)
    print("\nDone.")


if __name__ == "__main__":
    main()
