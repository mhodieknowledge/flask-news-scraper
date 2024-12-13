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

def fetch_rss_feed(rss_url, max_articles=10):
    """Fetch URLs, descriptions, titles, and other metadata from the RSS feed."""
    feed = feedparser.parse(rss_url)
    articles = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry and 'summary' in entry:
            article = {
                "title": entry.title,
                "url": entry.link,
                "description": html.unescape(entry.summary),  # Decode HTML entities in the description
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%Y-%m-%d %H:%M:%S')  # CAT time
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
                image_url = custom_image_url  # Use default for ZimEye or missing images

            return {"content": main_content, "image_url": image_url}
        else:
            return None
    except Exception as e:
        print(f"Error scraping {url}: {str(e)}")
        return None

def process_custom_rss_json(json_path, output_category):
    """
    Process custom RSS JSON files and scrape content for each link.
    
    :param json_path: Path to the input JSON file
    :param output_category: Category for output JSON file (e.g., business, local, sport)
    """
    try:
        # Define the GitHub raw URL for the custom RSS file
        github_json_url = f"https://raw.githubusercontent.com/{repo_owner}/{repo_name}/{branch}/{json_path}"
        
        # Fetch the JSON file directly using the raw URL
        response = requests.get(github_json_url)
        
        if response.status_code == 200:
            input_data = response.json()
        else:
            return f"Error: Unable to fetch {json_path} from GitHub. Status code: {response.status_code}"

        # Prepare output data
        output_data = {"news": []}

        # Iterate through links in the input JSON
        for item in input_data.get("news", []):
            url = item.get("href")
            title = item.get("title")
            
            if not url:
                continue
            
            # Scrape content for the URL
            scraped_content = scrape_article_content(url, content_class="post-body")
            
            if scraped_content:
                output_item = {
                    "title": title,
                    "url": url,
                    "content": scraped_content["content"],
                    "image_url": scraped_content["image_url"],
                    "time": datetime.now(pytz.timezone("Africa/Harare")).strftime("%Y-%m-%d %H:%M:%S"),
                }
                output_data["news"].append(output_item)

        # Save the processed data back to GitHub
        save_to_github(json_path, output_data)
        print(f"Successfully processed {json_path} and updated on GitHub.")

        return json_path
    except Exception as e:
        print(f"Error processing {json_path}: {str(e)}")
        return None

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
