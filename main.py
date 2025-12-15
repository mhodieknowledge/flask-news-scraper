# app.py
# Render-safe Flask news scraper
# FIXES:
# - RSS fetched via feedparser directly (no requests headers)
# - Removed Brotli (br) encoding issues
# - Better logging
# - Safer scraping defaults for Render IPs

import os
import requests
import random
import html
import re
import feedparser
import json
import base64
import time
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# -------------------- APP INIT --------------------
app = Flask(__name__)

# -------------------- CONFIG --------------------
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
repo_owner = "mhodieknowledge"
repo_name = "flask-news-scraper"
branch = "main"

TIMEZONE = pytz.timezone("Africa/Harare")

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
]

session = requests.Session()

# -------------------- FEEDS --------------------
feeds = {
    "chronicle": {
        "rss_url": "https://www.chronicle.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/chronicle.json",
    },
    "herald": {
        "rss_url": "https://www.herald.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/herald.json",
    },
    "newzimbabwe": {
        "rss_url": "https://www.newzimbabwe.com/feed/",
        "content_class": "post-body",
        "image_class": "post-media",
        "json_file": "news/newzimbabwe.json",
    },
    "zimeye": {
        "rss_url": "https://www.zimeye.net/feed/",
        "content_class": "page-content",
        "image_class": None,
        "json_file": "news/zimeye.json",
        "custom_image_url": "https://example.com/default.jpg",
    },
}

# -------------------- HELPERS --------------------

def headers():
    return {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
    }

# -------------------- RSS (RENDER SAFE) --------------------

def fetch_rss_feed(rss_url, max_articles=10):
    print(f"Fetching RSS: {rss_url}")

    feed = feedparser.parse(rss_url)

    if not feed.entries:
        print("⚠ RSS returned 0 entries (likely blocked upstream)")
        return []

    articles = []

    for entry in feed.entries[:max_articles]:
        if not hasattr(entry, "link"):
            continue

        summary_html = getattr(entry, "summary", "")
        soup = BeautifulSoup(html.unescape(summary_html), "html.parser")
        description = soup.get_text(strip=True)

        articles.append({
            "title": entry.title,
            "url": entry.link,
            "description": description,
            "time": datetime.now(TIMEZONE).strftime("%H:%M"),
            "date": datetime.now(TIMEZONE).strftime("%d %b %Y"),
        })

    print(f"✓ RSS articles found: {len(articles)}")
    return articles

# -------------------- ARTICLE SCRAPER --------------------

def scrape_article_content(url, content_class, image_class=None, custom_image_url=None):
    try:
        time.sleep(random.uniform(1.5, 3.5))
        r = session.get(url, headers=headers(), timeout=15)

        if r.status_code != 200:
            print(f"✗ Failed article {r.status_code}: {url}")
            return None

        if "cloudflare" in r.text.lower():
            print(f"⚠ Cloudflare block detected: {url}")
            return None

        soup = BeautifulSoup(r.text, "html.parser")

        content_div = soup.find("div", class_=content_class) or soup.find("article")
        if not content_div:
            return None

        paragraphs = [p.get_text(strip=True) for p in content_div.find_all("p") if p.get_text(strip=True)]
        content = "\n\n".join(paragraphs)

        image_url = custom_image_url

        if image_class:
            img_div = soup.find("div", class_=image_class)
            if img_div and img_div.find("img"):
                image_url = img_div.find("img").get("src")

        if not image_url:
            img = soup.find("img")
            if img:
                image_url = img.get("src")

        return {
            "content": content,
            "image_url": image_url,
        }

    except Exception as e:
        print("Article scrape error:", e)
        return None

# -------------------- GITHUB SAVE --------------------

def save_to_github(path, payload):
    api = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}"

    headers_gh = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    r = session.get(api, headers=headers_gh)
    sha = r.json().get("sha") if r.status_code == 200 else None

    content = base64.b64encode(json.dumps(payload, indent=2).encode()).decode()

    data = {
        "message": f"Update {path}",
        "content": content,
        "branch": branch,
    }
    if sha:
        data["sha"] = sha

    r = session.put(api, headers=headers_gh, json=data)
    return r.status_code in (200, 201)

# -------------------- MAIN SCRAPER --------------------

def scrape_and_save(feed):
    articles = fetch_rss_feed(feed["rss_url"], 10)
    output = {"news": []}

    for art in articles:
        data = scrape_article_content(
            art["url"],
            feed["content_class"],
            feed.get("image_class"),
            feed.get("custom_image_url"),
        )

        if not data:
            continue

        output["news"].append({
            **art,
            **data,
        })

    if not output["news"]:
        print("⚠ No articles scraped successfully")

    return save_to_github(feed["json_file"], output)

# -------------------- ROUTES --------------------

@app.route("/scrape/<feed_name>")
def scrape_feed(feed_name):
    if feed_name not in feeds:
        return jsonify({"error": "Feed not found"}), 404

    success = scrape_and_save(feeds[feed_name])

    if success:
        return jsonify({"message": f"Scraping completed for {feed_name}"})
    else:
        return jsonify({"error": "Scraping failed"}), 500

@app.route("/scrape/all")
def scrape_all():
    results = {}
    for name, feed in feeds.items():
        results[name] = "success" if scrape_and_save(feed) else "failed"
        time.sleep(random.uniform(4, 7))

    return jsonify(results)

# -------------------- RUN --------------------

if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
