import requests
import random
import html
import re
import feedparser
import json
import os
from flask import Flask, jsonify
from bs4 import BeautifulSoup

# Initialize Flask app
app = Flask(__name__)

# List of user agents for rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

# Custom image URL for zimeye.net
custom_url = "https://example.com/custom-image.jpg"

# Define the RSS feeds and their respective content and image classes
rss_sources = [
    {"rss": "https://zimeye.net/feed/", "content_class": "page-content", "image_class": None},
    {"rss": "https://herald.co.zw/feed/", "content_class": "post-content", "image_class": "s-post-thumbnail"},
    {"rss": "https://newzimbabwe.com/feed/", "content_class": "post-body", "image_class": "post-media"},
    {"rss": "https://chronicle.co.zw/feed/", "content_class": "post-content", "image_class": "s-post-thumbnail"}
]

def fetch_rss_feed(rss_url, max_articles=3):
    """Fetch RSS feed and return article URLs."""
    feed = feedparser.parse(rss_url)
    urls = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry:
            urls.append(entry.link)
    return urls

def scrape_article_content(url, content_class, image_class):
    """Scrape main content and image URL from an article page."""
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract main content
            content_div = soup.find("div", class_=content_class)
            if not content_div:
                return None, None
            paragraphs = content_div.find_all("p")
            processed_paragraphs = []
            for p in paragraphs:
                clean_text = html.unescape(p.get_text(strip=True))
                clean_text = re.sub(r'[^\x20-\x7E\n]', '', clean_text)
                if clean_text:
                    processed_paragraphs.append(clean_text)
            main_content = "\n\n".join(processed_paragraphs) + "\n\n"

            # Extract image URL
            if image_class:
                image_div = soup.find("div", class_=image_class)
                img_tag = image_div.find("img") if image_div else None
                image_url = img_tag["src"] if img_tag and "src" in img_tag.attrs else None
            else:
                image_url = custom_url  # For zimeye.net

            return main_content, image_url
        else:
            return None, None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None, None

def scrape_and_save(max_articles=3):
    """Scrape articles from multiple RSS feeds and save the data."""
    news_content = {"news": []}

    for source in rss_sources:
        rss_url = source["rss"]
        content_class = source["content_class"]
        image_class = source["image_class"]

        urls_to_scrape = fetch_rss_feed(rss_url, max_articles)
        for url in urls_to_scrape:
            print(f"Scraping {url}...")
            content, image_url = scrape_article_content(url, content_class, image_class)
            if content:
                news_content["news"].append({
                    "url": url,
                    "content": content,
                    "image_url": image_url
                })
            else:
                print(f"Failed to scrape {url}")

    # Save to news.json
    with open("news.json", "w") as json_file:
        json.dump(news_content, json_file, indent=4)
    print("News data saved successfully.")

@app.route('/scrape', methods=['GET'])
def scrape_news():
    """Trigger news scraping and return the status."""
    scrape_and_save(max_articles=3)
    return jsonify({"message": "Scraping completed and news.json updated!"}), 200

if __name__ == "__main__":
    app.run(debug=True)
