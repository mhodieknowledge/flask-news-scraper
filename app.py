import requests
import random
import html
import re
import feedparser
import json
import os
import time
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

# Custom URL for ZimEye
custom_url = "https://www.zimeye.net"  # Place your custom URL here

# RSS feed URLs and corresponding content/image div classes
rss_sources = [
    {
        "url": "https://www.zimeye.net/feed",
        "content_class": "page-content",
        "image_class": None,  # Custom URL handling
    },
    {
        "url": "https://www.herald.co.zw/feed",
        "content_class": "post-content",
        "image_class": "s-post-thumbnail",
    },
    {
        "url": "https://www.newzimbabwe.com/feed",
        "content_class": "post-body",
        "image_class": "post-media",
    },
    {
        "url": "https://www.chronicle.co.zw/feed",
        "content_class": "post-content",
        "image_class": "s-post-thumbnail",
    }
]

def fetch_rss_feed(rss_url, max_articles=1):
    feed = feedparser.parse(rss_url)
    urls = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry:
            urls.append(entry.link)
    return urls

def scrape_article_content(url, content_class, image_class, retries=3, delay=5):
    """Scrape main content and image URL from an article page with retries."""
    headers = {"User-Agent": random.choice(user_agents)}
    attempt = 0
    while attempt < retries:
        try:
            response = requests.get(url, headers=headers, timeout=30)  # Set timeout for the request
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
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
                    image_url = custom_url  # For ZimEye custom URL handling

                return main_content, image_url
            else:
                return None, None
        except requests.exceptions.RequestException as e:
            print(f"Attempt {attempt+1} failed: {e}")
            attempt += 1
            if attempt < retries:
                time.sleep(delay)  # Wait before retrying
    return None, None  # Return None if all retries fail

def scrape_and_save(rss_sources, max_articles=3):
    """Scrape content from multiple sources and save to GitHub."""
    news_content = {"news": []}
    
    for source in rss_sources:
        print(f"Scraping RSS Feed: {source['url']}...")
        urls_to_scrape = fetch_rss_feed(source['url'], max_articles)
        
        for url in urls_to_scrape:
            print(f"Scraping {url}...")
            content, image_url = scrape_article_content(url, source['content_class'], source['image_class'])
            if content:
                news_content["news"].append({
                    "url": url,
                    "content": content,
                    "image_url": image_url
                })
            else:
                print(f"Failed to scrape {url}")
    
    # Now using the GitHub API to update the file on GitHub
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = "zeroteq"  # Replace with your GitHub username
    repo_name = "flask-news-scraper"  # Replace with your GitHub repository name
    file_path = "news.json"
    branch = "main"

    # Get the current file content from GitHub
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Get the current content of the file on GitHub
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}?ref={branch}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        # If file exists, get the sha to update
        file_info = response.json()
        sha = file_info['sha']
    else:
        sha = None  # If file doesn't exist, no sha needed

    # Prepare data for commit
    data = {
        "message": "Update news.json with latest scraped articles",
        "content": json.dumps(news_content, indent=4).encode('utf-8').decode('utf-8'),  # File content in base64
        "branch": branch
    }

    if sha:
        data["sha"] = sha  # Add sha for existing file update

    # Make the request to update the file
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}"
    response = requests.put(url, headers=headers, json=data)

    if response.status_code == 201:
        print("News data saved successfully and pushed to GitHub")
    else:
        print(f"Failed to update GitHub: {response.status_code}, {response.text}")

@app.route('/scrape', methods=['GET'])
def scrape_news():
    """Trigger news scraping and return the status."""
    scrape_and_save(rss_sources)
    return jsonify({"message": "Scraping completed and news.json updated!"}), 200

if __name__ == "__main__":
    app.run(debug=True)
