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
    "local-news": "https://www.zbcnews.co.zw/category/local-news/",
    "sport": "https://www.zbcnews.co.zw/category/sport/",
}

json_files = {
    "business": "custom-rss/business.json",
    "local-news": "custom-rss/local.json",
    "sport": "custom-rss/sport.json",
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
                "description": html.unescape(entry.summary),
                "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
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
                "date":date
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

def find_image_url(article):
    """
    Try multiple methods to find the image URL for an article
    Returns the first found image URL or None
    """
    # Method 1: Look in the same article div for data-img-url
    img_tag = article.find("span", attrs={"data-img-url": True})
    if img_tag:
        return img_tag.get("data-img-url")
    
    # Method 2: Look for img tags with src attribute
    img_tag = article.find("img", src=True)
    if img_tag:
        return img_tag.get("src")
    
    # Method 3: Search for image in a wider context within the page
    # If the article div contains a link to the full article, 
    # try finding the image near that link
    article_link = article.find("a", href=True)
    if article_link:
        # Look in the parent or nearby divs for an image
        nearby_img = article_link.find_parent().find("img", src=True)
        if nearby_img:
            return nearby_img.get("src")
    
    # Method 4: If you know a specific pattern, add more targeted searches
    # For example, looking in a specific class or data attribute
    alternative_img_tag = article.find("div", class_="td-image-container").find("img", src=True) if article.find("div", class_="td-image-container") else None
    if alternative_img_tag:
        return alternative_img_tag.get("src")
    
    # If all methods fail, return None
    return None

def scrape_category_page(url, category_name):
    """Scrape a specific category page for articles, avoiding duplicates."""
    # Map the category to the expected display name (category_class)
    category_mapping = {
        "sport": "Sport",
        "local-news": "Local News",
        "business": "Business"
    }
    category_class = category_mapping.get(category_name, category_name.capitalize())  # Default to capitalized name

    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        
        # You might need to adjust this to find all potential article containers
        articles = soup.find_all(["div", "article"], class_=lambda x: x and ("module" in x or "article" in x))

        unique_hrefs = set()  # Use a set to track unique article URLs
        data = []

        for article in articles:
            # Get the category of the article
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category_class:
                # Get the title and href
                title_elem = article.find("p", class_="entry-title td-module-title").find("a")
                if title_elem:
                    title = title_elem.text.strip()
                    href = title_elem["href"]                    
                    
                    # Find image URL using multiple methods
                    img_url = find_image_url(article)
                    
                    # Avoid duplicate articles
                    if href not in unique_hrefs:
                        unique_hrefs.add(href)
                        data.append({
                            "title": title,
                            "href": href,
                            "img_url": img_url,  # This might be None if no image found
                            "category": category_class,
                            "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                            "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                        })
        
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

def scrape_custom_content(url):
    """Scrapes content from the given URL, excluding the last 3 paragraphs."""
    try:
        headers = {"User-Agent": random.choice(user_agents)}
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the specific div containing the content
            main_content = soup.find("div", class_="td-main-content-wrap td-container-wrap")
            
            # Fallback to another class if main_content is None
            if not main_content:
                main_content = soup.find("div", class_="tdc-container-wrap")
            
            if not main_content:
                return "Could not find the specified content div."
            
            # Extract paragraphs within the main content
            paragraphs = main_content.find_all("p")
            
            # Exclude the last 3 paragraphs
            filtered_paragraphs = exclude_last_paragraphs(paragraphs, 3)
            
            return "\n".join(p.get_text(strip=True) for p in filtered_paragraphs)
        else:
            return f"Failed to fetch the page at {url}. Status code: {response.status_code}"
    except Exception as e:
        return f"Error fetching URL {url}: {e}"

def exclude_last_paragraphs(paragraphs, count):
    """Excludes the last `count` paragraphs from a list."""
    return paragraphs[:-count] if len(paragraphs) > count else paragraphs

def scrape_custom_json(json_url, save_path):
    """ Scrape articles from a custom JSON file and save to GitHub. """
    try:
        # Fetch the JSON file
        response = requests.get(json_url)
        if response.status_code == 200:
            news_data = response.json()
            # Extract up to 4 articles
            news_articles = news_data.get("news", [])[:5]
            output_data = {"news": []}
            for news in news_articles:
                title = news.get("title", "")
                href = news.get("href", "")                
                if href:
                    content = scrape_custom_content(href)
                                 
                    # Append article data to the output list
                    output_data["news"].append({
                        "title": title,
                        "href": href,
                        "content": content,
                        "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                            "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')           
                    })
            # Save the data to GitHub
            save_to_github(save_path, output_data)
            return {"message": f"Scraping complete for {json_url}.", "articles": len(output_data["news"])}
        else:
            return {"error": f"Failed to fetch the JSON file. Status code: {response.status_code}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


@app.route('/scrape/custom/<category>', methods=['GET'])
def scrape_custom_category(category):
    """ Endpoint to scrape custom JSON files for specific categories. """
    custom_json_sources = {
        "sport": {
            "url": "https://raw.githubusercontent.com/zeroteq/flask-news-scraper/main/custom-rss/sport.json",
            "save_path": "zbc/sport.json"
        },
        "business": {
            "url": "https://raw.githubusercontent.com/zeroteq/flask-news-scraper/main/custom-rss/business.json",
            "save_path": "zbc/business.json"
        },
        "local-news": {
            "url": "https://raw.githubusercontent.com/zeroteq/flask-news-scraper/main/custom-rss/local.json",
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

if __name__ == "__main__":
    app.run(debug=False)
