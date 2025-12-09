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

# List of user agents for rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

# GitHub configuration
github_token = github_token = os.getenv('GITHUB_TOKEN')
repo_owner = "mhodieknowledge"
repo_name = "flask-news-scraper"
branch = "main"

# Feed configuration
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

# Category configuration
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


def fetch_rss_feed(rss_url, max_articles=10):
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry and 'summary' in entry:
            article = {
                "title": entry.title,
                "url": entry.link,
                "description": html.unescape(entry.summary),
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
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
            processed_paragraphs = []
            for p in paragraphs:
                clean_text = html.unescape(p.get_text(strip=True))
                clean_text = re.sub(r'[^\x20-\x7E\n]', '', clean_text)
                if clean_text:
                    processed_paragraphs.append(clean_text)
            main_content = "\n\n".join(processed_paragraphs) + "\n\n"

            if image_class:
                image_div = soup.find("div", class_=image_class)
                if image_div and image_div.img and image_div.img.get("src"):
                    image_url = image_div.img["src"]
                else:
                    image_url = custom_image_url
            else:
                image_url = custom_image_url

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
        date = article["date"]
        print(f"Scraping {url}...")
        data = scrape_article_content(url, content_class, image_class, custom_image_url)
        if data:
            news_content["news"].append({
                "title": title,
                "url": url,
                "content": data["content"],
                "image_url": data["image_url"],
                "description": description,
                "time": time,
                "date": date
            })
        else:
            print(f"Failed to scrape {url}")

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)

    sha = response.json()['sha'] if response.status_code == 200 else None

    file_content = json.dumps(news_content, indent=4)
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    data = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha

    response = requests.put(url, headers=headers, json=data)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub")
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")


def find_image_url(article):
    img_tag = article.find("span", attrs={"data-img-url": True})
    if img_tag:
        return img_tag.get("data-img-url")

    img_tag = article.find("img", src=True)
    if img_tag:
        return img_tag.get("src")

    article_link = article.find("a", href=True)
    if article_link:
        nearby_img = article_link.find_parent().find("img", src=True)
        if nearby_img:
            return nearby_img.get("src")

    alternative_img_tag = article.find("div", class_="td-image-container").find("img", src=True) if article.find("div", class_="td-image-container") else None
    if alternative_img_tag:
        return alternative_img_tag.get("src")

    return None

def scrape_category_page(url, category_name):
    category_mapping = {
        "sport": "Sport",
        "local-news": "Local News",
        "business": "Business"
    }
    category_class = category_mapping.get(category_name, category_name.capitalize())

    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all(["div", "article"], class_=lambda x: x and ("module" in x or "article" in x))

        unique_hrefs = set()
        data = []

        for article in articles:
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category_class:
                title_elem = article.find("p", class_="entry-title td-module-title").find("a")
                if title_elem:
                    title = title_elem.text.strip()
                    href = title_elem["href"]

                    img_url = find_image_url(article)

                    if href not in unique_hrefs:
                        unique_hrefs.add(href)
                        data.append({
                            "title": title,
                            "href": href,
                            "img_url": img_url,
                            "category": category_class,
                            "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                            "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                        })

        return data
    else:
        print(f"Failed to scrape {category_name}. Status code: {response.status_code}")
        return None

def save_to_github(json_file, data):
    file_content = json.dumps(data, indent=4)
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    response = requests.get(url, headers=headers)
    sha = response.json()["sha"] if response.status_code == 200 else None

    payload = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub.")
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")

@app.route('/scrape/<feed_name>', methods=['GET'])
def scrape_feed(feed_name):
    if feed_name in feeds:
        feed_data = feeds[feed_name]
        scrape_and_save_to_github(
            rss_url=feed_data["rss_url"],
            content_class=feed_data["content_class"],
            image_class=feed_data.get("image_class"),
            json_file=feed_data["json_file"],
            custom_image_url=feed_data.get("custom_image_url")
        )
        return jsonify({"message": f"Scraping completed for {feed_name}!"}), 200
    else:
        return jsonify({"error": "Feed not found"}), 404

def scrape_custom_content(url):
    try:
        headers = {"User-Agent": random.choice(user_agents)}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            main_content = soup.find("div", class_="td-main-content-wrap td-container-wrap")
            if not main_content:
                main_content = soup.find("div", class_="tdc-container-wrap")

            if not main_content:
                return "Could not find the specified content div."

            paragraphs = main_content.find_all("p")
            filtered_paragraphs = exclude_last_paragraphs(paragraphs, 3)

            return "\n".join(p.get_text(strip=True) for p in filtered_paragraphs)
        else:
            return f"Failed to fetch the page at {url}. Status code: {response.status_code}"
    except Exception as e:
        return f"Error fetching URL {url}: {e}"

def exclude_last_paragraphs(paragraphs, count):
    return paragraphs[:-count] if len(paragraphs) > count else paragraphs

def scrape_custom_json(json_url, save_path):
    try:
        response = requests.get(json_url)
        if response.status_code == 200:
            news_data = response.json()
            news_articles = news_data.get("news", [])[:5]
            output_data = {"news": []}
            for news in news_articles:
                title = news.get("title", "")
                href = news.get("href", "")
                if href:
                    content = scrape_custom_content(href)

                    output_data["news"].append({
                        "title": title,
                        "href": href,
                        "content": content,
                        "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                        "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                    })

            save_to_github(save_path, output_data)
            return {"message": f"Scraping complete for {json_url}.", "articles": len(output_data["news"])}
        else:
            return {"error": f"Failed to fetch the JSON file. Status code: {response.status_code}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.route('/scrape/custom/<category>', methods=['GET'])
def scrape_custom_category(category):
    custom_json_sources = {
        "sport": {
            "url": "https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/sport.json",
            "save_path": "zbc/sport.json"
        },
        "business": {
            "url": "https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/business.json",
            "save_path": "zbc/business.json"
        },
        "local-news": {
            "url": "https://raw.githubusercontent.com/mhodieknowledge/flask-news-scraper/main/custom-rss/local.json",
            "save_path": "zbc/local-news.json"
        }
    }
    if category in custom_json_sources:
        source = custom_json_sources[category]
        result = scrape_custom_json(source["url"], source["save_path"])
        if "error" in result:
            return jsonify(result), 500
        else:
            return jsonify(result), 200
    else:
        return jsonify({"error": "Category not found"}), 404

@app.route('/scrape/category/<category>', methods=['GET'])
def scrape_category(category):
    if category in categories:
        url = categories[category]
        json_file = json_files[category]
        data = scrape_category_page(url, category)

        if data:
            save_to_github(json_file, {"news": data})
            return jsonify({"message": f"Scraped {len(data)} articles for {category} and saved to GitHub."}), 200
        else:
            return jsonify({"error": f"Failed to scrape {category}."}), 500
    else:
        return jsonify({"error": "Category not found"}), 404

if __name__ == "__main__":
    app.run(debug=False)
