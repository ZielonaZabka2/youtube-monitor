#!/usr/bin/env python3
"""
Simulated YouTube monitor for testing when YouTube feeds are blocked.
This creates mock video data to test the summarization and Telegram workflow.
"""

import json
import os
from datetime import datetime, timezone

SAMPLE_VIDEOS = [
    {
        "title": "SEO Trends 2026: What You Need to Know",
        "channel": "Julian Goldie SEO",
        "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "video_id": "dQw4w9WgXcQ",
        "published": datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
        "transcript": "Today we're covering the latest SEO trends for 2026. First, let's talk about AI integration in search rankings. Google has announced that AI-generated content will now be evaluated based on its usefulness rather than its origin. This means you need to focus on providing genuine value. Key points: 1. User experience signals are more important than ever. Your site speed, mobile responsiveness, and navigation structure directly impact rankings. 2. E-E-A-T factors are crucial - Experience, Expertise, Authoritativeness, and Trustworthiness. Make sure your author bios are comprehensive. 3. Content clusters and topic modeling help search engines understand context better. 4. Featured snippets optimization requires structured data and clear, concise answers. 5. Local SEO for multi-location businesses requires schema markup and consistent NAP information."
    },
    {
        "title": "Building a 7-Figure YouTube Channel in 2026",
        "channel": "Itssssss Jack",
        "url": "https://www.youtube.com/watch?v=abc123defgh",
        "video_id": "abc123defgh",
        "published": datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
        "transcript": "Let's dive into building a 7-figure YouTube channel from scratch. I've helped dozens of creators reach this milestone. Here's the framework: First, niche selection is critical. Choose a niche that has demand, low competition, and where you have genuine expertise. The sweet spot is usually around 100K monthly searches. Second, content consistency beats quality sometimes. I recommend uploading weekly for the first year. Third, optimize your thumbnails and titles for CTR. We use A/B testing on all thumbnails. Fourth, engage with your community through comments and community posts. Fifth, collaborate with other creators in your niche. This exponentially increases your reach. The monetization strategy should include AdSense, sponsorships, and digital products. Most creators make 70% from products, not AdSense."
    }
]

def save_mock_videos():
    """Save mock videos to simulate monitor.py output"""
    with open("mock_output.txt", "w") as f:
        for video in SAMPLE_VIDEOS:
            f.write("SUMMARIZE_THIS_VIDEO:\n")
            f.write(f"TITLE: {video['title']}\n")
            f.write(f"CHANNEL: {video['channel']}\n")
            f.write(f"URL: {video['url']}\n")
            f.write(f"PUBLISHED: {video['published']}\n")
            f.write(f"TRANSCRIPT_AVAILABLE: True\n")
            f.write(f"TRANSCRIPT: {video['transcript']}\n")
            f.write("END_VIDEO\n")
            f.write("\n")

if __name__ == "__main__":
    save_mock_videos()
    print(f"Created mock output with {len(SAMPLE_VIDEOS)} sample videos")
