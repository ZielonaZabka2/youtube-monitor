#!/usr/bin/env python3
import requests, feedparser, re, sys, json, os
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"
CHANNELS = [
    "https://www.youtube.com/@JulianGoldieSEO",
    "https://www.youtube.com/@Itssssss_Jack",
    "https://www.youtube.com/@TimSEOGuru"
]
HEADERS = {"User-Agent": "Mozilla/5.0"}
STATE_FILE = "seen_videos.json"

def load_seen():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return set(json.load(f))
    return set()

def save_seen(seen):
    with open(STATE_FILE, "w") as f:
        json.dump(list(seen), f, indent=2)

def get_channel_id(url):
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        for p in [r'"channelId":"(UC[\w-]+)"', r'/channel/(UC[\w-]+)', r'"externalId":"(UC[\w-]+)"']:
            m = re.search(p, r.text)
            if m:
                return m.group(1)
    except Exception as e:
        print(f"Error: {e}")
    return None

def get_recent_videos(channel_id, hours=24):
    feed = feedparser.parse(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}")
    cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
    result = []
    for entry in feed.entries:
        try:
            pub = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
            if pub > cutoff:
                vid_id = entry.get("yt_videoid") or entry.link.split("v=")[-1]
                result.append({
                    "title": entry.title,
                    "url": entry.link,
                    "video_id": vid_id,
                    "channel": feed.feed.get("title", "Unknown"),
                    "published": pub.strftime("%d.%m.%Y %H:%M UTC")
                })
        except:
            pass
    return result

def get_transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "pl", "en-US"])
        return " ".join([x["text"] for x in t])[:6000]
    except:
        return None

def send_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10
    )
    return r.json()

# Main
seen = load_seen()
new_videos = []

for ch_url in CHANNELS:
    print(f"Checking {ch_url}...")
    ch_id = get_channel_id(ch_url)
    if not ch_id:
        print("  Could not get channel ID")
        continue
    videos = get_recent_videos(ch_id, hours=24)
    fresh = [v for v in videos if v["video_id"] not in seen]
    print(f"  Found {len(videos)} in 24h, {len(fresh)} new")
    new_videos.extend(fresh)

if not new_videos:
    now = datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M")
    send_telegram(f"✅ Sprawdzono kanały ({now} UTC) — brak nowych filmów.")
    print("No new videos.")
    sys.exit(0)

print(f"New videos to process: {len(new_videos)}")
for v in new_videos:
    transcript = get_transcript(v["video_id"])
    print("SUMMARIZE_THIS_VIDEO:")
    print(f"TITLE: {v['title']}")
    print(f"CHANNEL: {v['channel']}")
    print(f"URL: {v['url']}")
    print(f"PUBLISHED: {v['published']}")
    print(f"TRANSCRIPT_AVAILABLE: {transcript is not None}")
    if transcript:
        print(f"TRANSCRIPT: {transcript}")
    print("END_VIDEO")
    seen.add(v["video_id"])

save_seen(seen)
print(f"State saved: {len(seen)} total seen videos")
