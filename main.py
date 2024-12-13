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
github_token = os.getenv("GITHUB_TOKEN")
repo_owner = "zeroteq"
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
    "local": "https://www.zbcnews.co.zw/category/local-news/",
    "sport": "https://www.zbcnews.co.zw/category/sport/",
}

json_files = {
    "business": "custom-rss/business.json",
    "local": "custom-rss/local.json",
    "sport": "custom-rss/sport.json",
}

def exclude_last_paragraphs(paragraphs, exclude_count=3):
    """
    Excludes the last `exclude_count` paragraphs from the list.
    """
    return paragraphs[:-exclude_count] if len(paragraphs) > exclude_count else []

def fetch_rss_feed(rss_url, max_articles=10):
    """Fetch URLs, descriptions, titles, and other metadata from the RSS feed."""
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
    """Scrape article content and image URL from a URL."""
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract content
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

            # Extract image
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
    """Scrape articles from an RSS feed and save to GitHub."""
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

    # Using the GitHub API to update the file
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        file_info = response.json()
        sha = file_info['sha']
    else:
        sha = None

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

def scrape_category_page(url, category_name):
    """Scrape a specific category page for articles."""
    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("div", class_="td-module-meta-info")

        # Extract title and link
        data = []
        for article in articles:
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category_name.capitalize():
                title = article.find("p", class_="entry-title td-module-title").find("a").text.strip()
                href = article.find("p", class_="entry-title td-module-title").find("a")["href"]
                data.append({"title": title, "href": href})
        return data
    else:
        print(f"Failed to scrape {category_name}. Status code: {response.status_code}")
        return None

def save_to_github(json_file, data):
    """Save the scraped data to GitHub."""
    file_content = json.dumps(data, indent=4)
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")

    # GitHub API URL for the file
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if the file already exists
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info["sha"]
    else:
        sha = None

    # Prepare the request payload
    payload = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha

    # Make the PUT request to save the file
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub.")
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")

def scrape_zbc_content(url):
    """
    Scrape content from ZBC news pages with specific scraping mechanism.
    """
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Extract all <p> tags
            paragraphs = soup.find_all("p")

            # Exclude the last 3 paragraphs
            filtered_paragraphs = exclude_last_paragraphs(paragraphs)

            # Combine the remaining paragraphs' text
            main_content = "\n".join(p.get_text(strip=True) for p in filtered_paragraphs)

            return main_content
        else:
            print(f"Failed to fetch the page. Status code: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def def process_custom_rss_json(json_path, output_category):
    """
    Process custom RSS JSON files and scrape content for each link.
    
    :param json_path: Path to the input JSON file
    :param output_category: Category for output JSON file (e.g., business, local, sport)
    """
    try:
        # Define the GitHub path for the custom RSS file
        github_json_file = f"custom-rss/{output_category}.json"

        # Read the input JSON file from GitHub
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{github_json_file}?ref={branch}"
        headers = {
            "Authorization": f"Bearer {github_token}",
            "Accept": "application/vnd.github.v3+json",
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            file_info = response.json()
            file_content = base64.b64decode(file_info["content"]).decode("utf-8")
            input_data = json.loads(file_content)
        else:
            return f"Error: Unable to fetch {github_json_file} from GitHub. Status code: {response.status_code}"

        # Prepare output data
        output_data = {"news": []}

        # Iterate through links in the input JSON
        for item in input_data.get("news", []):
            url = item.get("href")
            title = item.get("title")
            
            if not url:
                continue
            
            # Scrape content for the URL
            scraped_content = scrape_zbc_content(url)
            
            if scraped_content:
                output_item = {
                    "title": title,
                    "url": url,
                    "content": scraped_content,
                    "time": datetime.now(pytz.timezone("Africa/Harare")).strftime("%Y-%m-%d %H:%M:%S"),
                }
                output_data["news"].append(output_item)

        # Save the processed data back to GitHub
        save_to_github(github_json_file, output_data)
        print(f"Successfully processed {github_json_file} and updated on GitHub.")

        return github_json_file
    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        return None

@app.route('/scrape/<feed_name>', methods=['GET'])
def scrape_feed(feed_name):
    """Scrape a specific feed by its name."""
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

@app.route('/scrape/category/<category>', methods=['GET'])
def scrape_category(category):
    """Endpoint to scrape a specific category and save data to GitHub."""
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

@app.route('/scrape/process-custom-rss/<filename>', methods=['GET'])
def process_specific_rss(filename):
    """
    Endpoint to process a specific custom RSS JSON file.
    
    :param filename: Name of the custom RSS JSON file (e.g., "business.json").
    """
    category = filename.split('.')[0]  # Extract category from filename
    json_file = f"custom-rss/{filename}"
    
    processed_file = process_custom_rss_json(json_file, category)
    
    if processed_file:
        return jsonify({
            "message": f"Processed {filename} successfully and updated on GitHub.",
            "file": processed_file
        }), 200
    else:
        return jsonify({"error": f"Failed to process {filename}."}), 500

if __name__ == "__main__":
    app.run(debug=True)
