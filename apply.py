#!/usr/bin/env python3
"""
Job Search Assistant — apply.py
Track and manage your job applications.

Usage:
  python apply.py          — show pipeline
  python apply.py add      — log a new application
  python apply.py update   — update an existing application
"""

import csv
import sys
from datetime import date
from pathlib import Path

try:
    import yaml
    _raw = yaml.safe_load(open("config.yaml", encoding="utf-8")) if Path("config.yaml").exists() else {}
    RESUME_OPTIONS = list((_raw.get("resumes") or {"default": "resume.pdf"}).keys())
except Exception:
    RESUME_OPTIONS = ["default"]

APPLICATIONS_FILE = Path("applications.csv")
FIELDS = [
    "date_applied", "title", "company", "url", "source",
    "resume", "cover_letter", "status", "follow_up_date", "notes",
]
STATUS_ORDER = [
    "Applied", "Phone Screen", "Interview", "Offer",
    "Rejected", "Withdrawn", "No Response",
]


def load() -> list[dict]:
    if not APPLICATIONS_FILE.exists():
        return []
    with open(APPLICATIONS_FILE, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def save(apps: list[dict]):
    with open(APPLICATIONS_FILE, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(apps)


def prompt(label: str, default: str = "") -> str:
    display = f" [{default}]" if default else ""
    val = input(f"{label}{display}: ").strip()
    return val if val else default


def show_pipeline(apps: list[dict]):
    if not apps:
        print("\nNo applications logged yet.  Run: python apply.py add\n")
        return

    by_status: dict[str, list] = {}
    for a in apps:
        by_status.setdefault(a.get("status", "Applied"), []).append(a)

    print(f"\n{'='*55}")
    print(f"  Application Pipeline  ({len(apps)} total)")
    print(f"{'='*55}")
    for status in STATUS_ORDER:
        group = by_status.get(status, [])
        if not group:
            continue
        print(f"\n  {status} ({len(group)})")
        for a in sorted(group, key=lambda x: x.get("date_applied", ""), reverse=True):
            fu = f"  → follow up {a['follow_up_date']}" if a.get("follow_up_date") else ""
            rv = f"  [{a['resume']}]" if a.get("resume") else ""
            print(f"    • {a['date_applied']}  {a['title']} @ {a['company']}{rv}{fu}")
            if a.get("notes"):
                print(f"               {a['notes']}")
    print()


def add_application():
    print("\n=== Log New Application ===\n")
    app = {}
    app["date_applied"] = prompt("Date applied", str(date.today()))
    app["title"]        = prompt("Job title")
    app["company"]      = prompt("Company")
    app["url"]          = prompt("URL")
    app["source"]       = prompt("Source (Indeed / LinkedIn / USAJobs / Other)")

    print(f"  Resume options: {' | '.join(RESUME_OPTIONS)}")
    app["resume"] = prompt("Resume used", RESUME_OPTIONS[0] if RESUME_OPTIONS else "")

    cl = prompt("Cover letter? (y/n)", "n").lower()
    app["cover_letter"] = "Yes" if cl == "y" else "No"

    print(f"  Status options: {' | '.join(STATUS_ORDER)}")
    app["status"]         = prompt("Status", "Applied")
    app["follow_up_date"] = prompt("Follow-up date (YYYY-MM-DD, or blank)", "")
    app["notes"]          = prompt("Notes", "")

    if not app["title"] or not app["company"]:
        print("\nTitle and company are required — nothing saved.\n")
        return

    apps = load()
    apps.append(app)
    save(apps)
    print(f"\nLogged: {app['title']} @ {app['company']}  ({app['status']})\n")


def update_application():
    apps = load()
    if not apps:
        print("\nNo applications to update.\n")
        return

    print("\n=== Update Application ===\n")
    for i, a in enumerate(apps, 1):
        print(f"  [{i:>2}] {a['date_applied']}  {a['title']} @ {a['company']}  — {a['status']}")

    raw = input("\nSelect number to update (or q to quit): ").strip()
    if raw.lower() == "q":
        return
    try:
        idx = int(raw) - 1
        app = apps[idx]
    except (ValueError, IndexError):
        print("Invalid selection.\n")
        return

    print(f"\nEditing: {app['title']} @ {app['company']}\n")
    print(f"  Status options: {' | '.join(STATUS_ORDER)}")
    app["status"]         = prompt("New status",     app.get("status", "Applied"))
    app["follow_up_date"] = prompt("Follow-up date", app.get("follow_up_date", ""))
    app["notes"]          = prompt("Notes",          app.get("notes", ""))

    apps[idx] = app
    save(apps)
    print(f"\nUpdated: {app['title']} @ {app['company']}  → {app['status']}\n")


if __name__ == "__main__":
    cmd = sys.argv[1].lower() if len(sys.argv) > 1 else "show"
    if cmd == "add":
        add_application()
    elif cmd == "update":
        update_application()
    else:
        show_pipeline(load())
