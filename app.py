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
    """Fetch URLs from the RSS feed."""
    feed = feedparser.parse(rss_url)
    urls = []
    for entry in feed.entries[:max_articles]:
        if 'link' in entry:
            urls.append(entry.link)
    return urls

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

def process_ai_response(response):
    """Process the AI's response and extract the title, description, and rephrased content."""
    if response['ok']:
        message = response['message']
        
        title = message.split("title: [")[1].split("]")[0].strip()
        description = message.split("description: [")[1].split("]")[0].strip()
        rephrased_content = message.split("rephrased_content: [")[1].split("]")[0].strip()

        return {
            "title": title,
            "description": description,
            "rephrased_content": rephrased_content
        }
    else:
        print("Error: AI response is not OK.")
        return None

def update_json_with_ai_data(json_data, ai_data):
    """Update the scraped JSON with the AI-generated title, description, and rephrased content."""
    for article in json_data['news']:
        article['title'] = ai_data['title']
        article['description'] = ai_data['description']
        article['rephrased_content'] = ai_data['rephrased_content']
    return json_data

def send_to_ai_and_update_json(scraped_content):
    """Send content to the AI API and update the JSON data with AI-generated content."""
    ai_url = "https://api.paxsenix.biz.id/ai/gpt4o"
    
    for article in scraped_content['news']:
        content = article['content']
        
        # Prepare the AI prompt
        prompt = f"without commenting or including any additional data ephrase the following news article and generate a title and description:\n\n{content}"
        
        # Send request to the AI API
        response = requests.get(f"{ai_url}?text={prompt}")
        ai_response = response.json()

        # Process AI response and extract relevant information
        ai_data = process_ai_response(ai_response)

        if ai_data:
            # Update the article with the AI-generated content
            article_data = update_json_with_ai_data(scraped_content, ai_data)
            print(f"Updated article data: {article_data}")
        else:
            print("Failed to process AI response.")

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

    # Send content to AI and update it
    send_to_ai_and_update_json(news_content)

    # Using the GitHub API to update the file
    github_token = os.getenv("GITHUB_TOKEN")
    repo_owner = "zeroteq"  # Replace with your GitHub username
    repo_name = "flask-news-scraper"  # Replace with your GitHub repository name
    branch = "main"

    # Prepare data for commit
    file_content = json.dumps(news_content, indent=4)
    
    # The process to update the content on GitHub is omitted for brevity, but you can follow the existing logic.
    # Here, you would send the updated content back to GitHub as you did earlier.

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
