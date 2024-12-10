import requests
import random
import html
import re
import feedparser
import json
import os
import base64
from git import Repo
from flask import Flask, request, jsonify
from bs4 import BeautifulSoup

# Initialize Flask app
app = Flask(__name__)

# List of user agents for rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
]

def fetch_rss_feed(rss_url, max_articles=3):
    feed = feedparser.parse(rss_url)
    urls = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry:
            urls.append(entry.link)
    return urls

def scrape_article_content(url):
    headers = {
        "User-Agent": random.choice(user_agents)
    }
    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            post_data_div = soup.find("div", class_="page-content")
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
            return main_content
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_and_save(rss_url, max_articles=3):
    urls_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}

    for url in urls_to_scrape:
        print(f"Scraping {url}...")
        content = scrape_article_content(url)
        if content:
            news_content["news"].append({
                "url": url,
                "content": content
            })
        else:
            print(f"Failed to scrape {url}")

    # Encode the content of the file to Base64 before pushing it to GitHub
    news_json = json.dumps(news_content, indent=4)
    encoded_content = base64.b64encode(news_json.encode()).decode()

    # Get GitHub token from environment variables
    github_token = os.getenv("GITHUB_TOKEN")

    # Define the GitHub API URL for updating the file in the repository
    url = "https://api.github.com/repos/zeroteq/flask-news-scraper/contents/news.json"

    # Prepare the data for the API request
    data = {
        "message": "Update news.json with latest scraped articles",
        "content": encoded_content,
        "branch": "main"
    }

    # Make the request to GitHub API to update the file
    response = requests.put(url, json=data, headers={
        "Authorization": f"token {github_token}"
    })

    if response.status_code == 200:
        print("News data successfully pushed to GitHub")
    else:
        print(f"Failed to update file on GitHub: {response.text}")

@app.route('/scrape', methods=['GET'])
def scrape_news():
    """Trigger news scraping and return the status."""
    rss_url = "https://www.zimeye.net/feed/"  # Example RSS feed URL
    scrape_and_save(rss_url)
    return jsonify({"message": "Scraping completed and news.json updated!"}), 200

if __name__ == "__main__":
    app.run(debug=True)
