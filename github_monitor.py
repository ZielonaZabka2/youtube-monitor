#!/usr/bin/env python3
import requests
import json
import os
import re
import sys
from datetime import datetime, timezone

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"
STATE_FILE = "seen_repos.json"

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def get_trending(since="daily"):
    url = f"https://github.com/trending?since={since}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    r = requests.get(url, headers=headers, timeout=15)
    repos = []

    # Parse repo blocks
    articles = re.findall(r'<article class="Box-row">(.*?)</article>', r.text, re.DOTALL)
    for article in articles:
        # Name
        name_match = re.search(r'href="/([^/]+/[^/"]+)"[^>]*>\s*\n\s*<span[^>]*>([^<]+)</span>\s*/\s*<span[^>]*>([^<]+)</span>', article)
        if not name_match:
            name_match2 = re.search(r'href="/([a-zA-Z0-9_.-]+/[a-zA-Z0-9_.-]+)"', article)
            if not name_match2:
                continue
            repo_path = name_match2.group(1).strip()
        else:
            repo_path = name_match.group(1).strip()

        # Description
        desc_match = re.search(r'<p\s+class="col-9[^"]*"[^>]*>\s*(.*?)\s*</p>', article, re.DOTALL)
        description = re.sub(r'\s+', ' ', desc_match.group(1)).strip() if desc_match else "Brak opisu"

        # Stars total
        stars_match = re.search(r'href="/' + re.escape(repo_path) + r'/stargazers"[^>]*>\s*[\s\S]*?([0-9,]+)\s*</a>', article)
        stars = stars_match.group(1).strip() if stars_match else "?"

        # Stars this period
        period_match = re.search(r'([0-9,]+)\s+stars\s+(?:today|this week)', article)
        stars_period = period_match.group(0).strip() if period_match else ""

        # Language
        lang_match = re.search(r'itemprop="programmingLanguage"[^>]*>([^<]+)<', article)
        language = lang_match.group(1).strip() if lang_match else "Unknown"

        repos.append({
            "name": repo_path,
            "url": f"https://github.com/{repo_path}",
            "description": description,
            "stars": stars,
            "stars_period": stars_period,
            "language": language
        })

    return repos

def send_telegram(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        if r.status_code == 200:
            return r.json()
        else:
            print(f"Telegram error {r.status_code}: {r.text[:100]}")
            return {"ok": False, "error": r.text}
    except Exception as e:
        print(f"Telegram send failed: {e}")
        return {"ok": False, "error": str(e)}

def format_repo(repo, index=None):
    prefix = f"{index}. " if index else ""
    lang = f" · {repo['language']}" if repo['language'] != 'Unknown' else ""
    period = f"\n⭐ {repo['stars_period']}" if repo['stars_period'] else ""
    return (
        f"{prefix}🔥 <b>{repo['name']}</b>{lang}\n"
        f"{repo['description']}\n"
        f"⭐ {repo['stars']} stars{period}\n"
        f"🔗 {repo['url']}"
    )

# --- Main ---
seen = load_seen()
today = datetime.now(timezone.utc)
is_friday = today.weekday() == 4  # 0=Monday, 4=Friday

print(f"Running GitHub monitor - {today.strftime('%Y-%m-%d %H:%M UTC')}")
print(f"Is Friday: {is_friday}")

# Daily trending - find new repos
daily_repos = get_trending("daily")
print(f"Daily trending: {len(daily_repos)} repos found")

new_repos = [r for r in daily_repos if r["name"] not in seen]
print(f"New repos (not seen before): {len(new_repos)}")

if new_repos:
    header = f"🚀 <b>GitHub Trending — nowe dziś</b> ({today.strftime('%d.%m.%Y')})\n"
    messages = [header]
    for repo in new_repos:
        messages.append(format_repo(repo))

    # Send in chunks (Telegram limit 4096 chars)
    chunk = messages[0]
    for msg in messages[1:]:
        if len(chunk) + len(msg) + 2 > 3800:
            send_telegram(chunk)
            chunk = msg
        else:
            chunk += "\n\n" + msg
    send_telegram(chunk)
    print(f"Sent {len(new_repos)} new repos to Telegram")

    # Update seen
    for r in new_repos:
        seen.add(r["name"])
else:
    now_str = today.strftime("%d.%m.%Y %H:%M")
    send_telegram(f"✅ GitHub Trending ({now_str} UTC) — brak nowych repozytoriów.")
    print("No new repos today.")

# Friday weekly summary
if is_friday:
    print("It's Friday! Sending weekly summary...")
    weekly_repos = get_trending("weekly")
    print(f"Weekly trending: {len(weekly_repos)} repos")

    if weekly_repos:
        header = f"📊 <b>GitHub TOP tygodnia</b> — piątkowe podsumowanie ({today.strftime('%d.%m.%Y')})\n"
        chunk = header
        for i, repo in enumerate(weekly_repos[:15], 1):
            msg = format_repo(repo, index=i)
            if len(chunk) + len(msg) + 2 > 3800:
                send_telegram(chunk)
                chunk = msg
            else:
                chunk += "\n\n" + msg
        send_telegram(chunk)
        print(f"Sent weekly top {min(15, len(weekly_repos))} repos")

save_seen(seen)
print(f"State saved: {len(seen)} total seen repos")
