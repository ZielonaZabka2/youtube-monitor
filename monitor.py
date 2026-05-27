#!/usr/bin/env python3
import requests, feedparser, re, sys, json, os, html, subprocess, tempfile, shutil, glob
from datetime import datetime, timezone, timedelta

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"
CHANNELS = [
    "https://www.youtube.com/@JulianGoldieSEO",
    "https://www.youtube.com/@Itssssss_Jack",
    "https://www.youtube.com/@TimSEOGuru"
]
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"}
STATE_FILE = "seen_videos.json"
TRANSCRIPT_LANGS = ["en", "en-US", "en-GB", "pl", "de", "es", "fr", "pt", "it"]
TRANSCRIPT_MAX_CHARS = 6000

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

def _transcript_via_api(video_id):
    """Try youtube-transcript-api v1.x API: manual -> generated -> translated -> any."""
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
    except ImportError as e:
        print(f"  [transcript-api] import failed: {e}")
        return None

    api = YouTubeTranscriptApi()
    try:
        tlist = api.list(video_id)
    except Exception as e:
        print(f"  [transcript-api] list() failed: {type(e).__name__}: {e}")
        return None

    def _fetch_safe(transcript, label):
        try:
            fetched = transcript.fetch()
            snippets = fetched.to_raw_data() if hasattr(fetched, "to_raw_data") else fetched
            text = " ".join(s["text"] for s in snippets if s.get("text"))
            if text.strip():
                print(f"  [transcript-api] got {label} ({transcript.language_code}, {len(text)} chars)")
                return text
        except Exception as e:
            print(f"  [transcript-api] fetch {label} failed: {type(e).__name__}: {e}")
        return None

    # 1) manually created in preferred languages
    try:
        t = tlist.find_manually_created_transcript(TRANSCRIPT_LANGS)
        text = _fetch_safe(t, "manual")
        if text:
            return text
    except Exception:
        pass

    # 2) auto-generated in preferred languages
    try:
        t = tlist.find_generated_transcript(TRANSCRIPT_LANGS)
        text = _fetch_safe(t, "generated")
        if text:
            return text
    except Exception:
        pass

    # 3) any transcript, translated to English if possible
    for t in tlist:
        if t.is_translatable:
            try:
                translated = t.translate("en")
                text = _fetch_safe(translated, f"translated-from-{t.language_code}")
                if text:
                    return text
            except Exception as e:
                print(f"  [transcript-api] translate from {t.language_code} failed: {e}")
        text = _fetch_safe(t, f"raw-{t.language_code}")
        if text:
            return text
    return None


def _transcript_via_ytdlp(video_id):
    """Fallback: use yt-dlp to download subtitles (uses Innertube, more robust)."""
    if not shutil.which("yt-dlp"):
        return None
    tmpdir = tempfile.mkdtemp(prefix="ytsub_")
    try:
        cmd = [
            "yt-dlp",
            "--skip-download",
            "--write-auto-subs",
            "--write-subs",
            "--sub-langs", ",".join(TRANSCRIPT_LANGS) + ",en.*",
            "--sub-format", "vtt/best",
            "--no-warnings",
            "-o", os.path.join(tmpdir, "%(id)s.%(ext)s"),
            f"https://www.youtube.com/watch?v={video_id}",
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        if res.returncode != 0:
            print(f"  [yt-dlp] exit {res.returncode}: {res.stderr.strip()[:200]}")
        vtt_files = sorted(glob.glob(os.path.join(tmpdir, "*.vtt")))
        if not vtt_files:
            return None
        # Prefer English files
        vtt_files.sort(key=lambda p: (0 if ".en" in os.path.basename(p) else 1, p))
        with open(vtt_files[0], encoding="utf-8") as f:
            raw = f.read()
        text = _vtt_to_text(raw)
        if text.strip():
            print(f"  [yt-dlp] got subtitles from {os.path.basename(vtt_files[0])} ({len(text)} chars)")
            return text
    except subprocess.TimeoutExpired:
        print("  [yt-dlp] timeout")
    except Exception as e:
        print(f"  [yt-dlp] error: {type(e).__name__}: {e}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
    return None


def _vtt_to_text(vtt):
    lines = []
    seen_lines = set()
    for raw_line in vtt.splitlines():
        line = raw_line.strip()
        if not line or line.startswith(("WEBVTT", "NOTE", "Kind:", "Language:")):
            continue
        if "-->" in line:
            continue
        if re.fullmatch(r"\d+", line):
            continue
        # strip inline timestamp tags like <00:00:05.000>
        line = re.sub(r"<[^>]+>", "", line)
        line = html.unescape(line).strip()
        if line and line not in seen_lines:
            seen_lines.add(line)
            lines.append(line)
    return " ".join(lines)


def _description_fallback(video_id):
    """Last resort: scrape video description from watch page."""
    try:
        r = requests.get(f"https://www.youtube.com/watch?v={video_id}", headers=HEADERS, timeout=10)
        m = re.search(r'"shortDescription":"((?:[^"\\]|\\.)*)"', r.text)
        if m:
            desc = m.group(1).encode("utf-8").decode("unicode_escape", errors="replace")
            desc = desc.replace("\\n", "\n").strip()
            if desc:
                print(f"  [description] got {len(desc)} chars from watch page")
                return f"[DESCRIPTION ONLY - transcript unavailable]\n{desc}"
    except Exception as e:
        print(f"  [description] failed: {type(e).__name__}: {e}")
    return None


def get_transcript(video_id):
    """Multi-source: transcript-api -> yt-dlp subs -> video description."""
    for fn in (_transcript_via_api, _transcript_via_ytdlp, _description_fallback):
        text = fn(video_id)
        if text:
            return text[:TRANSCRIPT_MAX_CHARS]
    print(f"  [transcript] no source worked for {video_id}")
    return None

def send_telegram(text):
    r = requests.post(
        f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
        json={"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"},
        timeout=10
    )
    return r.json()

def main():
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
        return 0

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
    return 0


if __name__ == "__main__":
    sys.exit(main())
