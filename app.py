import requests
import random
import html
import re
import feedparser
import json
import os
import base64
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

# Feed configuration
feeds = {
    "chronicle": {
        "rss_url": "https://www.chronicle.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "chronicle.json"
    },
    "newzimbabwe": {
        "rss_url": "https://www.newzimbabwe.com/feed/",
        "content_class": "post-body",
        "image_class": "post-media",
        "json_file": "newzimbabwe.json"
    },
    "zimeye": {
        "rss_url": "https://www.zimeye.net/feed/",
        "content_class": "page-content",
        "image_class": None,  # No images
        "json_file": "zimeye.json",
        "custom_image_url": "https://example.com/custom-image.jpg"
    },
    "herald": {
        "rss_url": "https://www.herald.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "herald.json"
    }
}

def fetch_rss_feed(rss_url, max_articles=3):
    """Fetch URLs from the RSS feed."""
    feed = feedparser.parse(rss_url)
    urls = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry:
            urls.append(entry.link)
    return urls

def scrape_article_content(url, content_class, image_class=None, custom_image_url=None):
    """Scrape and process article content and image URL from a URL."""
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Scrape main content
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
            main_content = "\n\n".join(processed_paragraphs)

            # Scrape image URL
            if image_class:
                image_div = soup.find("div", class_=image_class)
                image_url = image_div.img['src'] if image_div and image_div.img else None
            else:
                image_url = custom_image_url  # Fallback for ZimEye or missing images

            return {"content": main_content, "image_url": image_url}
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None, max_articles=3):
    """Scrape articles from an RSS feed and save to GitHub."""
    urls_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}

    for url in urls_to_scrape:
        print(f"Scraping {url}...")
        data = scrape_article_content(url, content_class, image_class, custom_image_url)
        if data:
            news_content["news"].append({
                "url": url,
                "content": data["content"],
                "image_url": data["image_url"]
            })
        else:
            print(f"Failed to scrape {url}")

    # Create the folder if it doesn't exist
    folder_name = "news_contents"
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Update the path to include the folder
    json_file_path = os.path.join(folder_name, json_file)

    # Using the GitHub API to update the file
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = "zeroteq"  # Replace with your GitHub username
    repo_name = "flask-news-scraper"  # Replace with your GitHub repository name
    branch = "main"

    # Prepare data for commit
    file_content = json.dumps(news_content, indent=4)
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')  # Proper Base64 encoding

    # Get file information from GitHub
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file_path}?ref={branch}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # If file exists, get the sha to update
        file_info = response.json()
        sha = file_info['sha']
    else:
        sha = None  # If file doesn't exist, no sha needed

    data = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": branch
    }
    if sha:
        data["sha"] = sha  # Add sha for existing file update

    # Make the request to update the file
    response = requests.put(url, headers=headers, json=data)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub")
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")

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

if __name__ == "__main__":
    app.run(debug=True)
