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
from textblob import TextBlob
from nltk.corpus import wordnet
import nltk

# Download necessary NLTK data files (use local storage on Vercel if needed)
nltk.data.path.append('/home/sbx_user1051/nltk_data')  # Adjust path if necessary for Vercel
nltk.download('punkt', download_dir='/home/sbx_user1051/nltk_data')
nltk.download('wordnet', download_dir='/home/sbx_user1051/nltk_data')

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
        "image_class": None,  # No image for ZimEye
        "json_file": "news/zimeye.json",
        "custom_image_url": "https://example.com/default-image.jpg"  # Replace with your default image URL
    },
    "herald": {
        "rss_url": "https://www.herald.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/herald.json"
    }
}

def fetch_rss_feed(rss_url, max_articles=3):
    """Fetch URLs and descriptions from the RSS feed."""
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry and 'summary' in entry:
            article = {
                "url": entry.link,
                "description": html.unescape(entry.summary)  # Decode HTML entities in the description
            }
            articles.append(article)
    return articles

def rephrase_text(text):
    """Rephrase text using TextBlob and WordNet for synonyms."""
    blob = TextBlob(text)
    words = blob.words
    rephrased_words = []
    
    for word in words:
        synonyms = wordnet.synsets(word)
        if synonyms:
            # Replace with a synonym if available
            synonym = synonyms[0].lemmas()[0].name().replace("_", " ")
            rephrased_words.append(synonym)
        else:
            rephrased_words.append(word)  # Keep the original word
    
    rephrased_text = " ".join(rephrased_words)
    return rephrased_text

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
                image_url = custom_image_url  # Use default for ZimEye or missing images

            return {"content": main_content, "image_url": image_url}
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None, max_articles=3):
    """Scrape articles from an RSS feed and save to GitHub."""
    articles_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}

    for article in articles_to_scrape:
        url = article["url"]
        description = rephrase_text(article["description"])  # Rephrase description
        print(f"Scraping {url}...")
        data = scrape_article_content(url, content_class, image_class, custom_image_url)
        if data:
            rephrased_content = rephrase_text(data["content"])  # Rephrase content
            news_content["news"].append({
                "url": url,
                "content": rephrased_content,
                "image_url": data["image_url"],
                "description": description
            })
        else:
            print(f"Failed to scrape {url}")

    # Save to GitHub (unchanged logic)
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = "zeroteq"  # Replace with your GitHub username
    repo_name = "flask-news-scraper"  # Replace with your GitHub repository name
    branch = "main"

    # Prepare data for commit
    file_content = json.dumps(news_content, indent=4)
    encoded_content = base64.b64encode(file_content.encode('utf-8')).decode('utf-8')

    # Get file information from GitHub
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
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
