#!/usr/bin/env python3
import requests, re, sys, json, os, xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"
CHANNELS = [
    "https://www.youtube.com/@JulianGoldieSEO",
    "https://www.youtube.com/@Itssssss_Jack",
    "https://www.youtube.com/@TimSEOGuru"
]
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
}
STATE_FILE = "seen_videos.json"
TEST_MODE = os.getenv("YT_TEST_MODE", "").lower() == "true"

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
        import subprocess
        result = subprocess.run(['yt-dlp', '--flat-playlist', '-j', url],
                               capture_output=True, timeout=10, text=True)
        if result.returncode == 0:
            data = json.loads(result.stdout.split('\n')[0])
            if 'channel_id' in data:
                return data['channel_id']
            elif 'uploader_id' in data:
                return data['uploader_id']
    except:
        pass

    # Fallback: try pattern matching
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        patterns = [
            r'"channelId":"(UC[\w-]+)"',
            r'/channel/(UC[\w-]+)',
            r'"externalId":"(UC[\w-]+)"'
        ]
        for p in patterns:
            m = re.search(p, r.text)
            if m:
                return m.group(1)
    except Exception as e:
        print(f"  Error: {e}")
    return None

def get_recent_videos(channel_id, hours=24):
    try:
        resp = requests.get(f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}",
                           headers=HEADERS, timeout=10)
        root = ET.fromstring(resp.content)
        ns = {'yt': 'http://www.youtube.com/xml/schemas/2015/12/subscription',
              'atom': 'http://www.w3.org/2005/Atom'}
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        result = []
        channel_title = root.find('atom:title', ns)
        channel_name = channel_title.text if channel_title is not None else "Unknown"
        for entry in root.findall('atom:entry', ns):
            try:
                title_elem = entry.find('atom:title', ns)
                link_elem = entry.find('atom:link', ns)
                pub_elem = entry.find('atom:published', ns)
                vid_id_elem = entry.find('yt:videoId', ns)

                title = title_elem.text if title_elem is not None else "Unknown"
                link = link_elem.get('href') if link_elem is not None else ""
                pub_str = pub_elem.text if pub_elem is not None else ""
                vid_id = vid_id_elem.text if vid_id_elem is not None else ""

                pub = datetime.fromisoformat(pub_str.replace('Z', '+00:00'))
                if pub > cutoff:
                    result.append({
                        "title": title,
                        "url": link,
                        "video_id": vid_id,
                        "channel": channel_name,
                        "published": pub.strftime("%d.%m.%Y %H:%M UTC")
                    })
            except:
                pass
        return result
    except Exception as e:
        print(f"Error fetching videos: {e}")
        return []

def get_transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        t = YouTubeTranscriptApi.get_transcript(video_id, languages=["en", "pl", "en-US"])
        return " ".join([x["text"] for x in t])[:6000]
    except:
        return None

def send_telegram(text):
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
            timeout=10
        )
        try:
            return r.json()
        except:
            print(f"  Telegram response: {r.status_code}")
            return {"ok": False}
    except Exception as e:
        print(f"  Telegram error: {e}")
        return {"ok": False}

# Main
seen = load_seen()
new_videos = []

if TEST_MODE:
    # Test data for demonstration
    print("Running in TEST MODE with example data...")
    new_videos = [
        {
            "title": "Advanced SEO Strategies for 2026",
            "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            "video_id": "dQw4w9WgXcQ",
            "channel": "Julian Goldie SEO",
            "published": "23.05.2026 14:30 UTC",
            "transcript": "In this video we'll cover the latest SEO techniques..."
        }
    ]
else:
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
