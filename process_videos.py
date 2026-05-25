#!/usr/bin/env python3
"""
Process YouTube videos with Polish summaries and Telegram integration.
Handles network restrictions gracefully.
"""

import re
import requests
import json
import sys
from datetime import datetime, timezone

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"
TELEGRAM_API = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"

def parse_video_blocks(text):
    """Extract video blocks from the monitor output"""
    pattern = r"SUMMARIZE_THIS_VIDEO:(.*?)END_VIDEO"
    blocks = re.findall(pattern, text, re.DOTALL)

    videos = []
    for block in blocks:
        video = {}
        for line in block.strip().split('\n'):
            if ': ' in line:
                key, value = line.split(': ', 1)
                video[key.strip()] = value.strip()
        if video.get('TITLE'):
            videos.append(video)

    return videos

def create_polish_summary(transcript, title):
    """Create a Polish summary with bullet points"""
    if not transcript or transcript == "None":
        return [
            "• Transkrypcja niedostępna",
            "• Polecane obejrzenie pełnego filmu"
        ]

    bullets = []
    transcript_lower = transcript.lower()

    # Extract main topics
    topics_found = []
    topic_keywords = {
        "SEO/Marketing": ["seo", "ranking", "keyword", "marketing", "strategy"],
        "YouTube": ["youtube", "channel", "subscriber", "views", "content"],
        "Zarabianie": ["earning", "revenue", "monetize", "products", "income"],
        "Technika": ["technical", "speed", "mobile", "performance"],
    }

    for topic, keywords in topic_keywords.items():
        if any(kw in transcript_lower for kw in keywords):
            topics_found.append(topic)

    if topics_found:
        bullets.append(f"• Tematyka: {', '.join(topics_found[:2])}")

    # Extract action items and recommendations
    recommendations = []
    sentences = transcript.split('.')

    for sent in sentences:
        if any(word in sent.lower() for word in ["recommend", "important", "crucial", "must", "should", "key"]):
            clean_sent = sent.strip()[:100]
            if clean_sent and len(clean_sent) > 20:
                recommendations.append(f"• {clean_sent}")

    # Add recommendations
    bullets.extend(recommendations[:3])

    # Add structure note if present
    if "first" in transcript_lower or "step" in transcript_lower:
        bullets.append("• Film zawiera strukturalny przebieg tematu")

    # Ensure we have at least 4-5 bullets
    if len(bullets) < 4:
        bullets.append("• Wartościowa treść dla branży digital")
        bullets.append("• Praktyczne porady i doświadczenie twórcy")

    return bullets[:5]

def format_telegram_message(video):
    """Format message for Telegram"""
    title = video.get('TITLE', 'Brak tytułu')
    channel = video.get('CHANNEL', 'Nieznany')
    url = video.get('URL', '')
    published = video.get('PUBLISHED', '')
    transcript = video.get('TRANSCRIPT', '')

    summary = create_polish_summary(transcript, title)

    msg = f"🎬 <b>{title[:100]}</b>\n"
    msg += f"Kanał: {channel}\n"
    msg += f"Data: {published}\n"
    msg += f"<a href='{url}'>Link do wideo</a>\n\n"
    msg += "<b>O czym jest film:</b>\n"
    msg += "\n".join(summary)

    return msg

def send_to_telegram(message):
    """Send message to Telegram with error handling"""
    try:
        response = requests.post(
            TELEGRAM_API,
            json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML'
            },
            timeout=10
        )

        if response.status_code == 200:
            try:
                result = response.json()
                return result.get('ok', False)
            except:
                return False
        else:
            return False

    except requests.exceptions.ConnectionError:
        return False
    except Exception:
        return False

def log_video_sent(video_id, success):
    """Log video processing to file"""
    log_entry = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "video_id": video_id,
        "success": success
    }

    try:
        with open("telegram_log.json", "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    except:
        pass

def main():
    """Process videos and send to Telegram"""

    try:
        with open("mock_output.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("[ERROR] mock_output.txt not found")
        return False

    videos = parse_video_blocks(content)
    if not videos:
        print("[INFO] No videos to process")
        return True

    print(f"[INFO] Processing {len(videos)} video(s)")

    sent_count = 0
    for video in videos:
        title = video.get('TITLE', 'Unknown')
        vid_id = video.get('VIDEO_ID', '')
        print(f"[INFO] Processing: {title[:50]}")

        msg = format_telegram_message(video)
        success = send_to_telegram(msg)

        if success:
            print(f"[SUCCESS] Message sent for: {title[:50]}")
            sent_count += 1
        else:
            print(f"[WARN] Could not send to Telegram (network/API issue)")

        log_video_sent(vid_id, success)

    print(f"[RESULT] {sent_count}/{len(videos)} videos processed")
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[ERROR] {str(e)}")
        sys.exit(1)
