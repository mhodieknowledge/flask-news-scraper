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

# User agents
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

# GitHub configuration (Render ENV VAR)
github_token = os.getenv("GITHUB_TOKEN")
repo_owner = "mhodieknowledge"
repo_name = "flask-news-scraper"
branch = "main"

# RSS feeds
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

# ZBC categories
categories = {
    "business": "https://www.zbcnews.co.zw/category/business/",
    "local-news": "https://www.zbcnews.co.zw/category/local-news/",
    "sport": "https://www.zbcnews.co.zw/category/sport/",
}

json_files = {
    "business": "custom-rss/business.json",
    "local-news": "custom-rss/local.json",
    "sport": "custom-rss/sport.json",
}

# --------------------------------------------------
# RSS FETCH (FIXED DESCRIPTION)
# --------------------------------------------------
def fetch_rss_feed(rss_url, max_articles=10):
    feed = feedparser.parse(rss_url)
    articles = []

    for entry in feed.entries[:max_articles]:
        if "link" in entry and "summary" in entry:

            clean_summary = re.sub(
                r'<p class="link-more".*?</p>',
                '',
                entry.summary,
                flags=re.DOTALL
            )

            clean_summary = BeautifulSoup(
                clean_summary, "html.parser"
            ).get_text(strip=True)

            articles.append({
                "title": entry.title,
                "url": entry.link,
                "description": html.unescape(clean_summary),
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
            })

    return articles

# --------------------------------------------------
# ARTICLE CONTENT SCRAPER
# --------------------------------------------------
def scrape_article_content(url, content_class, image_class=None, custom_image_url=None):
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return None

        soup = BeautifulSoup(response.text, "html.parser")
        post_data_div = soup.find("div", class_=content_class)
        if not post_data_div:
            return None

        paragraphs = post_data_div.find_all("p")
        processed = []

        for p in paragraphs:
            text = html.unescape(p.get_text(strip=True))
            text = re.sub(r'[^\x20-\x7E\n]', '', text)
            if text and "Continue reading" not in text:
                processed.append(text)

        content = "\n\n".join(processed) + "\n\n"

        if image_class:
            image_div = soup.find("div", class_=image_class)
            image_url = image_div.img["src"] if image_div and image_div.img else custom_image_url
        else:
            image_url = custom_image_url

        return {"content": content, "image_url": image_url}

    except Exception as e:
        print(f"Error scraping {url}: {e}")
        return None

# --------------------------------------------------
# SCRAPE RSS + SAVE
# --------------------------------------------------
def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None):
    articles = fetch_rss_feed(rss_url)
    output = {"news": []}

    for article in articles:
        data = scrape_article_content(
            article["url"],
            content_class,
            image_class,
            custom_image_url
        )
        if data:
            output["news"].append({
                "title": article["title"],
                "url": article["url"],
                "content": data["content"],
                "image_url": data["image_url"],
                "description": article["description"],
                "time": article["time"],
                "date": article["date"]
            })

    save_to_github(json_file, output)

# --------------------------------------------------
# GITHUB SAVE
# --------------------------------------------------
def save_to_github(json_file, data):
    encoded = base64.b64encode(
        json.dumps(data, indent=4).encode()
    ).decode()

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json"
    }

    r = requests.get(url, headers=headers)
    sha = r.json().get("sha") if r.status_code == 200 else None

    payload = {
        "message": f"Update {json_file}",
        "content": encoded,
        "branch": branch
    }
    if sha:
        payload["sha"] = sha

    requests.put(url, headers=headers, json=payload)

# --------------------------------------------------
# ZBC HELPERS
# --------------------------------------------------
def find_image_url(article):
    for img in article.find_all("img", src=True):
        return img["src"]
    return None

def scrape_category_page(url, category_name):
    mapping = {
        "sport": "Sport",
        "local-news": "Local News",
        "business": "Business"
    }
    category_class = mapping.get(category_name)

    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return None

    soup = BeautifulSoup(response.content, "html.parser")
    articles = soup.find_all(["div", "article"])

    data = []
    seen = set()

    for article in articles:
        category_tag = article.find("a", class_="td-post-category")
        if category_tag and category_tag.text.strip() == category_class:
            title_elem = article.find("a", href=True)
            if title_elem:
                href = title_elem["href"]
                if href not in seen:
                    seen.add(href)
                    data.append({
                        "title": title_elem.get_text(strip=True),
                        "href": href,
                        "img_url": find_image_url(article),
                        "category": category_class,
                        "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                        "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                    })
    return data

def scrape_custom_content(url):
    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)
    if response.status_code != 200:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    content = soup.find("div", class_="td-main-content-wrap")
    if not content:
        return ""

    paragraphs = content.find_all("p")[:-3]
    return "\n".join(p.get_text(strip=True) for p in paragraphs)

def scrape_custom_json(json_url, save_path):
    response = requests.get(json_url)
    if response.status_code != 200:
        return {"error": "Failed to fetch source JSON"}

    source = response.json().get("news", [])[:5]
    output = {"news": []}

    for item in source:
        content = scrape_custom_content(item.get("href"))
        output["news"].append({
            "title": item.get("title"),
            "href": item.get("href"),
            "content": content,
            "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
            "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
        })

    save_to_github(save_path, output)
    return {"message": "ZBC scrape complete", "articles": len(output["news"])}

# --------------------------------------------------
# ROUTES
# --------------------------------------------------
@app.route("/scrape/<feed>")
def scrape_feed(feed):
    if feed not in feeds:
        return jsonify({"error": "Feed not found"}), 404

    f = feeds[feed]
    scrape_and_save_to_github(
        f["rss_url"],
        f["content_class"],
        f.get("image_class"),
        f["json_file"],
        f.get("custom_image_url")
    )
    return jsonify({"message": f"{feed} scraped"}), 200

@app.route("/scrape/category/<category>")
def scrape_category(category):
    if category not in categories:
        return jsonify({"error": "Category not found"}), 404

    data = scrape_category_page(categories[category], category)
    if not data:
        return jsonify({"error": "Failed"}), 500

    save_to_github(json_files[category], {"news": data})
    return jsonify({"message": f"{len(data)} ZBC articles scraped"}), 200

@app.route("/scrape/custom/<category>")
def scrape_custom(category):
    sources = {
        "sport": ("https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/sport.json", "zbc/sport.json"),
        "business": ("https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/business.json", "zbc/business.json"),
        "local-news": ("https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/local.json", "zbc/local-news.json"),
    }

    if category not in sources:
        return jsonify({"error": "Category not found"}), 404

    result = scrape_custom_json(*sources[category])
    return jsonify(result), 200

# --------------------------------------------------
# START
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=False)
