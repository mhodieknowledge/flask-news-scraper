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

app = Flask(__name__)

user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

github_token = os.getenv("GITHUB_TOKEN")
repo_owner = "zeroteq"
repo_name = "flask-news-scraper"
branch = "main"

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

categories = {
    "business": "https://www.zbcnews.co.zw/category/business/",
    "local": "https://www.zbcnews.co.zw/category/local-news/",
    "sport": "https://www.zbcnews.co.zw/category/sport/",
}

json_files = {
    "business": "custom-rss/business.json",
    "local": "custom-rss/local.json",
    "sport": "custom-rss/sport.json",
}

def fetch_rss_feed(rss_url, max_articles=10):
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry and 'summary' in entry:
            article = {
                "title": entry.title,
                "url": entry.link,
                "description": html.unescape(entry.summary),
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%Y-%m-%d %H:%M:%S')
            }
            articles.append(article)
    return articles

def scrape_article_content(url, content_class, image_class=None, custom_image_url=None):
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            post_data_div = soup.find("div", class_=content_class)
            if not post_data_div:
                return None
            paragraphs = post_data_div.find_all("p")
            processed_paragraphs = [
                re.sub(r'[^\x20-\x7E\n]', '', html.unescape(p.get_text(strip=True)))
                for p in paragraphs if p.get_text(strip=True)
            ]
            main_content = "\n\n".join(processed_paragraphs) + "\n\n"
            image_url = (
                soup.find("div", class_=image_class).img["src"]
                if image_class and soup.find("div", class_=image_class) and soup.find("div", class_=image_class).img
                else custom_image_url
            )
            return {"content": main_content, "image_url": image_url}
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None, max_articles=10):
    articles_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}

    for article in articles_to_scrape:
        url = article["url"]
        description = article["description"]
        title = article["title"]
        time = article["time"]
        print(f"Scraping {url}...")
        data = scrape_article_content(url, content_class, image_class, custom_image_url)
        if data:
            news_content["news"].append({
                "title": title,
                "url": url,
                "content": data["content"],
                "image_url": data["image_url"],
                "description": description,
                "time": time
            })
        else:
            print(f"Failed to scrape {url}")

    save_to_github(json_file, news_content)

def save_to_github(json_file, data):
    file_content = json.dumps(data, indent=4)
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)
    sha = response.json().get("sha") if response.status_code == 200 else None
    payload = {"message": f"Update {json_file}", "content": encoded_content, "branch": branch}
    if sha:
        payload["sha"] = sha
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub.")
    else:
        print(f"Failed to update {json_file}: {response.status_code}, {response.text}")

def process_category_from_json(category):
    os.makedirs('zbc', exist_ok=True)
    json_file = json_files[category]
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            category_data = json.load(f)
        scraped_articles = []
        for article in category_data.get('news', []):
            url = article.get('href') or article.get('url')
            if not url:
                continue
            headers = {"User-Agent": random.choice(user_agents)}
            response = requests.get(url, headers=headers)
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                paragraphs = soup.find_all("p")[:-3] if len(soup.find_all("p")) > 3 else soup.find_all("p")
                main_content = "\n".join(p.get_text(strip=True) for p in paragraphs)
                scraped_articles.append({'title': article["title"], 'url': url, 'content': main_content})
        with open(f'zbc/{category}.json', 'w', encoding='utf-8') as f:
            json.dump(scraped_articles, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error processing {category}: {e}")

@app.route('/scrape/<feed_name>', methods=['GET'])
def scrape_feed(feed_name):
    if feed_name in feeds:
        scrape_and_save_to_github(**feeds[feed_name])
        return jsonify({"message": f"Scraping completed for {feed_name}!"}), 200
    else:
        return jsonify({"error": "Feed not found"}), 404

@app.route('/scrape/category/<category>', methods=['GET'])
def scrape_category(category):
    if category in categories:
        data = scrape_category_page(categories[category], category)
        save_to_github(json_files[category], {"news": data})
        return jsonify({"message": f"Scraped category: {category}!"}), 200
    return jsonify({"error": "Category not found"}), 404

@app.route('/scrape/category/individual/<category>', methods=['GET'])
def scrape_category_individual(category):
    if category in json_files:
        process_category_from_json(category)
        return jsonify({"message": f"Processed category: {category} successfully!"}), 200
    else:
        return jsonify({"error": "Category not found"}), 404

if __name__ == "__main__":
    app.run(debug=True)
