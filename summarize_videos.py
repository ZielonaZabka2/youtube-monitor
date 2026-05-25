#!/usr/bin/env python3
"""
Process YouTube video transcripts and send Polish summaries to Telegram.
"""

import re
import requests
import json

TELEGRAM_TOKEN = "8766055278:AAEPUD-t4kZA6yADNRwfVyKvSqTiUYUZ-jw"
CHAT_ID = "6813645463"

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

def summarize_transcript_polish(transcript, title):
    """Create a Polish summary from the transcript"""
    if not transcript or transcript == "None":
        return ["Transkrypcja niedostępna"]

    # Extract key points from transcript
    transcript_lower = transcript.lower()

    # Topic detection
    topics = {
        "SEO": ["seo", "ranking", "google", "optimization", "keyword"],
        "YouTube": ["youtube", "channel", "subscriber", "views"],
        "Content": ["content", "writing", "blog", "article"],
        "Marketing": ["marketing", "campaign", "strategy", "traffic"],
        "Monetization": ["monetization", "revenue", "earnings", "products"],
        "Technical": ["technical", "speed", "mobile", "schema", "structured data"],
    }

    found_topics = []
    for topic, keywords in topics.items():
        if any(kw in transcript_lower for kw in keywords):
            found_topics.append(topic)

    # Create Polish bullet points
    bullets = []

    # Main topic
    if found_topics:
        topic_str = " i ".join(found_topics[:2])
        bullets.append(f"Główne tematy: {topic_str}")

    # Extract sentences with key information
    sentences = [s.strip() for s in transcript.split('.') if s.strip() and len(s.split()) > 5]

    # Add important sentences as bullet points
    if "focus on" in transcript_lower or "important" in transcript_lower:
        for sent in sentences:
            if any(word in sent.lower() for word in ["crucial", "important", "key", "must", "recommend"]):
                bullets.append(f"• {sent.strip()[:80]}")
                if len(bullets) >= 4:
                    break

    # Add framework/steps if available
    if "first" in transcript_lower and "second" in transcript_lower:
        bullets.append("• Film zawiera strukturalny framework z wieloma krokami")

    # Add best practices if available
    if "best practice" in transcript_lower or "tip" in transcript_lower:
        bullets.append("• Zawiera praktyczne wskazówki i best practices")

    # Default bullet points based on content length
    if len(bullets) < 4:
        if len(transcript) > 1000:
            bullets.append("• Szczegółowa analiza tematu z praktycznymi poradami")
            bullets.append("• Warte obejrzenia dla osób pracujących w branży")
        else:
            bullets.append("• Krótkie, skupione wyjaśnienie zagadnienia")

    return bullets[:5]

def format_telegram_message(video):
    """Format video summary for Telegram"""
    title = video.get('TITLE', 'Brak tytułu')
    channel = video.get('CHANNEL', 'Nieznany kanał')
    url = video.get('URL', '')
    published = video.get('PUBLISHED', 'Brak daty')
    transcript = video.get('TRANSCRIPT', '')

    # Generate Polish summary
    summary_bullets = summarize_transcript_polish(transcript, title)

    # Format message
    message = f"🎬 <b>{title[:80]}</b>\n"
    message += f"Kanał: <b>{channel}</b>\n"
    message += f"Data: {published}\n"
    message += f"<a href='{url}'>Obejrzyj na YouTube</a>\n\n"
    message += "<b>O czym jest film:</b>\n"
    for bullet in summary_bullets:
        if bullet.startswith("•"):
            message += f"{bullet}\n"
        else:
            message += f"• {bullet}\n"

    return message

def send_to_telegram(message):
    """Send message to Telegram"""
    try:
        response = requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            json={
                'chat_id': CHAT_ID,
                'text': message,
                'parse_mode': 'HTML',
                'disable_web_page_preview': False
            },
            timeout=10
        )

        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print("✓ Wiadomość wysłana do Telegram")
                return True
            else:
                print(f"✗ Telegram error: {result.get('description', 'Unknown')}")
                return False
        else:
            print(f"✗ HTTP {response.status_code}: {response.text[:100]}")
            return False

    except Exception as e:
        print(f"✗ Błąd wysyłania: {str(e)[:100]}")
        return False

def main():
    """Main processing function"""

    # Read mock output
    try:
        with open("mock_output.txt", "r", encoding="utf-8") as f:
            content = f.read()
    except FileNotFoundError:
        print("Plik mock_output.txt nie znaleziony")
        return

    # Parse videos
    videos = parse_video_blocks(content)
    print(f"Znaleziono {len(videos)} filmów do przetworzenia\n")

    # Process each video
    success_count = 0
    for i, video in enumerate(videos, 1):
        print(f"--- Film {i}/{len(videos)}: {video.get('TITLE', 'Brak tytułu')[:50]} ---")

        # Format message
        message = format_telegram_message(video)
        print(f"Wiadomość ({len(message)} znaków):")
        print(message[:200] + "...\n")

        # Send to Telegram
        if send_to_telegram(message):
            success_count += 1

        print()

    print(f"Podsumowanie: {success_count}/{len(videos)} filmów wysłanych")

    return success_count > 0

if __name__ == "__main__":
    main()
