import json
import os
import requests
from datetime import datetime, date

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
SEEN_FILE = "seen_repos.json"


def load_seen():
    if os.path.exists(SEEN_FILE):
        with open(SEEN_FILE) as f:
            return set(json.load(f))
    return set()


def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        json.dump(list(seen), f)


def fetch_trending(since="daily"):
    url = f"https://gh-trending-api.deta.dev/repositories?since={since}"
    try:
        r = requests.get(url, timeout=15)
        r.raise_for_status()
        return r.json()
    except Exception:
        # fallback scraping
        return fetch_trending_scrape(since)


def fetch_trending_scrape(since="daily"):
    url = f"https://github.com/trending?since={since}"
    headers = {"User-Agent": "Mozilla/5.0"}
    r = requests.get(url, headers=headers, timeout=15)
    repos = []
    for line in r.text.splitlines():
        if 'href="/' in line and 'article' not in line:
            pass
    # parse html manually
    from html.parser import HTMLParser

    class TrendParser(HTMLParser):
        def __init__(self):
            super().__init__()
            self.repos = []
            self.in_h2 = False
            self.current = {}

        def handle_starttag(self, tag, attrs):
            attrs = dict(attrs)
            if tag == "h2" and "class" in attrs and "h3" in attrs.get("class", ""):
                self.in_h2 = True
            if self.in_h2 and tag == "a" and "href" in attrs:
                href = attrs["href"].strip("/")
                parts = href.split("/")
                if len(parts) == 2:
                    self.current = {"author": parts[0], "name": parts[1], "url": f"https://github.com/{href}"}
                    self.in_h2 = False

        def handle_endtag(self, tag):
            if tag == "article" and self.current:
                self.repos.append(self.current)
                self.current = {}

    parser = TrendParser()
    parser.feed(r.text)
    return parser.repos or []


def send_telegram(text):
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print(f"[TELEGRAM SKIP] {text[:80]}")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "HTML"}, timeout=10)


def format_repo(repo):
    name = repo.get("name", "?")
    author = repo.get("author", "?")
    description = repo.get("description", "") or ""
    stars = repo.get("stars", repo.get("stargazers_count", "?"))
    url = repo.get("url", f"https://github.com/{author}/{name}")
    lang = repo.get("language", "") or ""
    lang_str = f" | {lang}" if lang else ""
    return f"⭐ <b>{author}/{name}</b>{lang_str}\n{description[:120]}\n🔗 {url}\n⭐ {stars}"


def main():
    print(f"[{datetime.now()}] Starting GitHub Trending Monitor")

    seen = load_seen()
    daily_repos = fetch_trending("daily")
    print(f"Fetched {len(daily_repos)} trending repos")

    new_repos = [r for r in daily_repos if f"{r.get('author')}/{r.get('name')}" not in seen]
    print(f"New repos (not seen before): {len(new_repos)}")

    if new_repos:
        send_telegram(f"🔥 <b>GitHub Trending — {len(new_repos)} nowych repo!</b>")
        for repo in new_repos[:10]:
            key = f"{repo.get('author')}/{repo.get('name')}"
            send_telegram(format_repo(repo))
            seen.add(key)
    else:
        print("No new repos to send.")

    # Friday: weekly TOP 15
    if date.today().weekday() == 4:
        print("It's Friday — sending weekly TOP 15")
        weekly = fetch_trending("weekly")
        msg = "📊 <b>GitHub TOP 15 tygodnia:</b>\n\n"
        for i, repo in enumerate(weekly[:15], 1):
            name = repo.get("name", "?")
            author = repo.get("author", "?")
            url = repo.get("url", f"https://github.com/{author}/{name}")
            msg += f"{i}. <a href='{url}'>{author}/{name}</a>\n"
        send_telegram(msg)

    save_seen(seen)
    print(f"Saved {len(seen)} seen repos to {SEEN_FILE}")


if __name__ == "__main__":
    main()
