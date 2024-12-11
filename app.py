import requests
import random
import html
import re
import feedparser
import json
import os
import base64
import urllib.parse
from flask import Flask, jsonify
from bs4 import BeautifulSoup

# Initialize Flask app
app = Flask(__name__)

# Custom AI API configuration
AI_API_BASE_URL = "https://api.paxsenix.biz.id/ai/gpt4o"

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

def call_custom_ai_api(prompt):
    """
    Call custom AI API with a given prompt.
    
    Args:
        prompt (str): The prompt to send to the AI API
    
    Returns:
        str: AI-generated response or original text if API call fails
    """
    try:
        # URL encode the prompt
        encoded_prompt = urllib.parse.quote(prompt)
        
        # Construct full API URL
        full_url = f"{AI_API_BASE_URL}?text={encoded_prompt}"
        
        # Make the API request
        response = requests.get(full_url)
        
        # Check if request was successful
        if response.status_code == 200:
            # Parse JSON response
            response_data = response.json()
            
            # Check if response is successful and contains a message
            if response_data.get('ok', False) and 'message' in response_data:
                return response_data['message']
        
        # Fallback if API call fails
        print(f"AI API call failed. Status code: {response.status_code}")
        return prompt
    
    except Exception as e:
        print(f"Error calling AI API: {str(e)}")
        return prompt

def rephrase_content(original_content, max_length=1000):
    """
    Rephrase the content using custom AI API.
    
    Args:
        original_content (str): The text to be rephrased
        max_length (int): Maximum length of content to process
    
    Returns:
        str: Rephrased content
    """
    # Truncate content if too long
    truncated_content = original_content[:max_length]
    
    # Construct prompt for rephrasing
    rephrase_prompt = f"""
    Please rephrase the following text while maintaining its original meaning. 
    Use different sentence structures and vocabulary to make it unique:

    {truncated_content}
    
    Rephrased version:"""
    
    # Call AI API
    rephrased_text = call_custom_ai_api(rephrase_prompt)
    
    return rephrased_text.strip()

def generate_ai_title_description(content, max_length=1000):
    """
    Generate a title and description using custom AI API.
    
    Args:
        content (str): The text to generate metadata for
        max_length (int): Maximum length of content to process
    
    Returns:
        dict: Contains 'title' and 'description'
    """
    # Truncate content if too long
    truncated_content = content[:max_length]
    
    # Construct prompt for title and description generation
    metadata_prompt = f"""
    Based on the following text, generate:
    1. A catchy, concise title
    2. A brief, engaging description
    
    Text:
    {truncated_content}
    
    Format your response as:
    Title: [Your concise title here]
    Description: [Your brief description here]"""
    
    # Call AI API
    metadata_response = call_custom_ai_api(metadata_prompt)
    
    # Parse the response
    try:
        # Split response into title and description
        lines = metadata_response.split('\n')
        title = lines[0].replace('Title:', '').strip()
        description = lines[1].replace('Description:', '').strip() if len(lines) > 1 else ""
        
        return {
            "title": title or "News Article",
            "description": description or "Latest news from the source"
        }
    except Exception as e:
        print(f"Error parsing AI metadata: {str(e)}")
        return {
            "title": "News Article",
            "description": "Latest news from the source"
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

def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None, max_articles=3):
    """Scrape articles from an RSS feed and save to GitHub."""
    urls_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}

    for url in urls_to_scrape:
        print(f"Scraping {url}...")
        data = scrape_article_content(url, content_class, image_class, custom_image_url)
        if data:
            # Rephrase the content
            rephrased_content = rephrase_content(data["content"])
            
            # Generate AI title and description
            ai_metadata = generate_ai_title_description(data["content"])
            
            news_content["news"].append({
                "url": url,
                "original_content": data["content"],
                "rephrased_content": rephrased_content,
                "image_url": data["image_url"],
                "ai_title": ai_metadata["title"],
                "ai_description": ai_metadata["description"]
            })
        else:
            print(f"Failed to scrape {url}")

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
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
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
