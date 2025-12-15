import os
import requests
import random
import html
import re
import feedparser
import json
import base64
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Initialize Flask app
app = Flask(__name__)

# Rotate user agents
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

# GitHub config (Render ENV VAR)
github_token = os.getenv("GITHUB_TOKEN")
repo_owner = "mhodieknowledge"
repo_name = "flask-news-scraper"
branch = "main"

# Feeds
feeds = {
    "chronicle": {
        "rss_url": "https://www.chronicle.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/chronicle.json"
    },
    "newzimbabwe": {
        "rss_url": "https://www.newzimbabwe.com/feed/",
        "content_class": "post-body",
        "image_class": "post-media",
        "json_file": "news/newzimbabwe.json"
    },
    "zimeye": {
        "rss_url": "https://www.zimeye.net/feed/",
        "content_class": "page-content",
        "image_class": None,
        "json_file": "news/zimeye.json",
        "custom_image_url": "https://example.com/default-image.jpg"
    },
    "herald": {
        "rss_url": "https://www.herald.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/herald.json"
    }
}

# --------------------------------------------------
# RSS FETCH (FIXED: removes "Continue reading")
# --------------------------------------------------
def fetch_rss_feed(rss_url, max_articles=10):
    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries[:max_articles]:
        if "link" in entry and "summary" in entry:

            # REMOVE <p class="link-more">...</p>
            clean_summary = re.sub(
                r'<p class="link-more".*?</p>',
                '',
                entry.summary,
                flags=re.DOTALL
            )

            # Optional: strip remaining HTML
            clean_summary = BeautifulSoup(clean_summary, "html.parser").get_text(strip=True)

            articles.append({
                "title": entry.title,
                "url": entry.link,
                "description": html.unescape(clean_summary),
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
            })

    return articles

# --------------------------------------------------
# ARTICLE SCRAPER
# --------------------------------------------------
def scrape_article_content(url, content_class, image_class=None, custom_image_url=None):
    headers = {"User-Agent": random.choice(user_agents)}

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        content_div = soup.find("div", class_=content_class)
        if not content_div:
            return None

        paragraphs = content_div.find_all("p")
        clean_paragraphs = []

        for p in paragraphs:
            text = html.unescape(p.get_text(strip=True))
            text = re.sub(r'[^\x20-\x7E\n]', '', text)
            if text and "Continue reading" not in text:
                clean_paragraphs.append(text)

        content = "\n\n".join(clean_paragraphs) + "\n\n"

        if image_class:
            img_div = soup.find("div", class_=image_class)
            image_url = img_div.img["src"] if img_div and img_div.img else custom_image_url
        else:
            image_url = custom_image_url

        return {"content": content, "image_url": image_url}

    except Exception as e:
        print(f"Scrape error: {e}")
        return None

# --------------------------------------------------
# SCRAPE + SAVE TO GITHUB
# --------------------------------------------------
def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None):
    articles = fetch_rss_feed(rss_url)
    output = {"news": []}

    for article in articles:
        print(f"Scraping {article['url']}")
        scraped = scrape_article_content(
            article["url"],
            content_class,
            image_class,
            custom_image_url
        )

        if scraped:
            output["news"].append({
                "title": article["title"],
                "url": article["url"],
                "content": scraped["content"],
                "image_url": scraped["image_url"],
                "description": article["description"],
                "time": article["time"],
                "date": article["date"]
            })

    save_json_to_github(json_file, output)

# --------------------------------------------------
# GITHUB SAVE
# --------------------------------------------------
def save_json_to_github(path, data):
    content = base64.b64encode(
        json.dumps(data, indent=4).encode()
    ).decode()

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{path}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": f"Update {path}",
        "content": content,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    r = requests.put(url, headers=headers, json=payload)
    print(f"{path} → {r.status_code}")

# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.route("/scrape/<feed_name>")
def scrape_feed(feed_name):
    if feed_name not in feeds:
        return jsonify({"error": "Feed not found"}), 404

    feed = feeds[feed_name]
    scrape_and_save_to_github(
        feed["rss_url"],
        feed["content_class"],
        feed.get("image_class"),
        feed["json_file"],
        feed.get("custom_image_url")
    )

    return jsonify({"message": f"{feed_name} scraping completed"}), 200

# --------------------------------------------------
# START
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
