#!/usr/bin/env python3
"""
Test version with mock data to verify the workflow
Channel IDs (manually obtained):
- JulianGoldieSEO: UC7_d9AzpkSAoW-P37uNb4eQ
- Itssssss_Jack: UC_SOME_ID (placeholder)  
- TimSEOGuru: UC_ANOTHER_ID (placeholder)
"""
import json
from datetime import datetime, timezone, timedelta

# Mock video data
MOCK_VIDEOS = [
    {
        "title": "10 SEO Hacks That Actually Work in 2024",
        "channel": "Julian Goldie SEO",
        "url": "https://www.youtube.com/watch?v=aBcDeFgHiJk",
        "video_id": "aBcDeFgHiJk",
        "published": datetime.now(timezone.utc).strftime("%d.%m.%Y %H:%M UTC"),
        "transcript": "Today we're going to talk about SEO hacks that actually work in 2024. First, let's focus on technical SEO. You need to make sure your site is fast, mobile-friendly, and has proper schema markup. Second, link building is still crucial. You should focus on getting high-quality backlinks from authoritative sites. Third, content quality matters more than ever. Write long-form, comprehensive content that solves user problems. We also discussed the importance of user experience signals, proper header tags, and keyword research."
    }
]

# Load existing seen videos
STATE_FILE = "seen_videos.json"
try:
    with open(STATE_FILE) as f:
        seen = set(json.load(f))
except:
    seen = set()

print("Checking YouTube channels...")
new_videos = [v for v in MOCK_VIDEOS if v["video_id"] not in seen]

if not new_videos:
    print("No new videos found")
    import sys
    sys.exit(0)

print(f"Found {len(new_videos)} new video(s) to process")

for v in new_videos:
    print("\nSUMMAMRIZE_THIS_VIDEO:")
    print(f"TITLE: {v['title']}")
    print(f"CHANNEL: {v['channel']}")
    print(f"URL: {v['url']}")
    print(f"PUBLISHED: {v['published']}")
    print(f"TRANSCRIPT: {v['transcript']}")
    print("END_VIDEO")
    seen.add(v["video_id"])

# Save state
with open(STATE_FILE, "w") as f:
    json.dump(list(seen), f, indent=2)
print(f"\nState saved: {len(seen)} total videos")
