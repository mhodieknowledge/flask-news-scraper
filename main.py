import os
import requests
import random
import html
import re
import feedparser
import json
import base64
import time
from flask import Flask, jsonify
from bs4 import BeautifulSoup
from datetime import datetime
import pytz

# Initialize Flask app
app = Flask(__name__)

# Enhanced list of user agents for rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Edge/120.0.0.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
]

# GitHub configuration
github_token = os.getenv('GITHUB_TOKEN')
repo_owner = "mhodieknowledge"
repo_name = "flask-news-scraper"
branch = "main"

# Feed configuration
feeds = {
    "chronicle": {
        "rss_url": "https://www.chronicle.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/chronicle.json",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
    },
    "newzimbabwe": {
        "rss_url": "https://www.newzimbabwe.com/feed/",
        "content_class": "post-body",
        "image_class": "post-media",
        "json_file": "news/newzimbabwe.json",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }
    },
    "zimeye": {
        "rss_url": "https://www.zimeye.net/feed/",
        "content_class": "page-content",
        "image_class": None,
        "json_file": "news/zimeye.json",
        "custom_image_url": "https://example.com/default-image.jpg",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        }
    },
    "herald": {
        "rss_url": "https://www.herald.co.zw/feed/",
        "content_class": "post--content",
        "image_class": "s-post-thumbnail",
        "json_file": "news/herald.json",
        "headers": {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Cache-Control": "max-age=0",
        }
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

# Create a requests session for better performance and cookie handling
session = requests.Session()
# Initialize session with a default user agent
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
})

def get_enhanced_headers(additional_headers=None):
    """Get enhanced headers with anti-detection measures"""
    base_headers = {
        "User-Agent": random.choice(user_agents),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Cache-Control": "max-age=0",
    }
    
    if additional_headers:
        base_headers.update(additional_headers)
    
    return base_headers

def fetch_rss_feed(rss_url, max_articles=10):
    """Fetch RSS feed with retry logic"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            headers = get_enhanced_headers()
            response = requests.get(rss_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                feed = feedparser.parse(response.content)
                articles = []
                for entry in feed.entries[:max_articles]:
                    if 'link' in entry and 'summary' in entry:
                        # Parse the HTML description with BeautifulSoup
                        soup = BeautifulSoup(html.unescape(entry.summary), 'html.parser')
                        
                        # Remove the unwanted "Continue reading" link
                        link_more = soup.find('p', class_='link-more')
                        if link_more:
                            link_more.decompose()  # Remove it completely
                        
                        # Also look for any other similar patterns
                        for tag in soup.find_all(['p', 'div'], class_=lambda x: x and ('more-link' in x or 'continue-reading' in x or 'read-more' in x)):
                            tag.decompose()
                        
                        # Get the cleaned text
                        description = soup.get_text(strip=True)
                        
                        article = {
                            "title": entry.title,
                            "url": entry.link,
                            "description": description,
                            "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                            "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                        }
                        articles.append(article)
                return articles
            else:
                print(f"Attempt {attempt + 1}: Failed to fetch RSS feed. Status: {response.status_code}")
                
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error fetching RSS feed: {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (attempt + 1))  # Exponential backoff
    
    return []

def scrape_article_content(url, content_class, image_class=None, custom_image_url=None, site_headers=None):
    """Scrape article content with enhanced anti-blocking measures"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Add random delay between requests to appear more human-like
            time.sleep(random.uniform(1, 3))
            
            # Get headers for this specific site
            headers = get_enhanced_headers(site_headers)
            headers["Referer"] = url.rsplit('/', 2)[0] + '/' if '/' in url else url
            
            # Use a new session for each request to avoid cookie tracking
            temp_session = requests.Session()
            temp_session.headers.update(headers)
            
            response = temp_session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Try multiple selectors if the primary one fails
                post_data_div = soup.find("div", class_=content_class)
                if not post_data_div:
                    # Try alternative selectors
                    alternative_selectors = [
                        "article",
                        "main",
                        "div.post-content",
                        "div.entry-content",
                        "div.article-content",
                        "div.content",
                        "div.story-body"
                    ]
                    for selector in alternative_selectors:
                        post_data_div = soup.find(selector)
                        if post_data_div:
                            break
                
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
                
                # Find image with multiple fallbacks
                image_url = custom_image_url
                
                if image_class:
                    image_div = soup.find("div", class_=image_class)
                    if image_div and image_div.img and image_div.img.get("src"):
                        image_url = image_div.img["src"]
                
                # If no image found, try common image selectors
                if not image_url or image_url == custom_image_url:
                    image_selectors = [
                        "img.featured-image",
                        "img.wp-post-image",
                        "img.attachment-post-thumbnail",
                        "img.entry-thumbnail",
                        "figure img",
                        ".post-thumbnail img",
                        ".article-image img",
                        "main img"
                    ]
                    
                    for selector in image_selectors:
                        img_tag = soup.select_one(selector)
                        if img_tag and img_tag.get("src"):
                            image_url = img_tag["src"]
                            break
                
                # Last resort: look for any image in the article
                if not image_url or image_url == custom_image_url:
                    all_images = soup.find_all("img")
                    for img in all_images:
                        src = img.get("src")
                        if src and ("http" in src or "https" in src):
                            # Prefer larger images (check size in attributes)
                            if img.get("width") and int(img.get("width", 0)) > 300:
                                image_url = src
                                break
                            elif img.get("height") and int(img.get("height", 0)) > 200:
                                image_url = src
                                break
                
                return {"content": main_content, "image_url": image_url}
            
            elif response.status_code in [403, 429, 503]:
                print(f"Attempt {attempt + 1}: Blocked/rate limited for {url}. Status: {response.status_code}")
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1) * random.uniform(1, 2)
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
            else:
                print(f"Attempt {attempt + 1}: Failed to scrape {url}. Status: {response.status_code}")
                break
                
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: Timeout for {url}")
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error scraping {url}: {str(e)}")
        
        if attempt < max_retries - 1:
            time.sleep(retry_delay * (attempt + 1))
    
    return None

def scrape_and_save_to_github(rss_url, content_class, image_class, json_file, custom_image_url=None, max_articles=10, site_headers=None):
    articles_to_scrape = fetch_rss_feed(rss_url, max_articles)
    news_content = {"news": []}
    
    print(f"Found {len(articles_to_scrape)} articles to scrape")
    
    for i, article in enumerate(articles_to_scrape):
        url = article["url"]
        description = article["description"]
        title = article["title"]
        time_str = article["time"]
        date_str = article["date"]
        
        print(f"Scraping {i+1}/{len(articles_to_scrape)}: {url}...")
        
        data = scrape_article_content(url, content_class, image_class, custom_image_url, site_headers)
        
        if data:
            news_content["news"].append({
                "title": title,
                "url": url,
                "content": data["content"],
                "image_url": data["image_url"],
                "description": description,
                "time": time_str,
                "date": date_str
            })
            print(f"Successfully scraped: {title[:50]}...")
        else:
            print(f"Failed to scrape {url}")
        
        # Add delay between scraping different articles
        if i < len(articles_to_scrape) - 1:
            delay = random.uniform(2, 5)
            time.sleep(delay)
    
    # Save to GitHub
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{json_file}?ref={branch}"
    headers = {
        "Authorization": f"Bearer {github_token}",
        "Accept": "application/vnd.github.v3+json",
    }
    
    try:
        response = session.get(url, headers=headers, timeout=10)
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
        
        response = session.put(url, headers=headers, json=data, timeout=10)
        if response.status_code in (200, 201):
            print(f"{json_file} updated successfully on GitHub with {len(news_content['news'])} articles")
            return True
        else:
            print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")
            return False
    except Exception as e:
        print(f"Error saving to GitHub: {str(e)}")
        return False

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
    
    headers = get_enhanced_headers()
    
    # Use a new session for each request
    temp_session = requests.Session()
    temp_session.headers.update(headers)
    
    response = temp_session.get(url, timeout=15)
    
    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all(["div", "article"], class_=lambda x: x and ("module" in x or "article" in x))
        
        unique_hrefs = set()
        data = []
        
        for article in articles:
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category_class:
                title_elem = article.find("p", class_="entry-title td-module-title")
                if title_elem:
                    title_link = title_elem.find("a")
                    if title_link:
                        title = title_link.text.strip()
                        href = title_link["href"]
                        
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
    
    response = session.get(url, headers=headers, timeout=10)
    sha = response.json()["sha"] if response.status_code == 200 else None
    
    payload = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": branch,
    }
    if sha:
        payload["sha"] = sha
    
    response = session.put(url, headers=headers, json=payload, timeout=10)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub.")
        return True
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")
        return False

def scrape_custom_content(url):
    """Scrape content from ZBC news articles with anti-blocking measures"""
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        try:
            # Add random delay
            time.sleep(random.uniform(2, 4))
            
            # Use simpler headers
            headers = {
                "User-Agent": random.choice(user_agents),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            }
            
            # Use a fresh session for each attempt
            temp_session = requests.Session()
            temp_session.headers.update(headers)
            
            response = temp_session.get(url, timeout=15)
            
            if response.status_code == 200:
                soup = BeautifulSoup(response.text, "html.parser")
                
                # Try multiple content selectors for ZBC
                content_selectors = [
                    "div.td-post-content",
                    "div.td-main-content-wrap",
                    "div.tdc-container-wrap",
                    "article",
                    "div.entry-content",
                    "div.post-content",
                    "main",
                ]
                
                main_content = None
                for selector in content_selectors:
                    main_content = soup.select_one(selector)
                    if main_content:
                        break
                
                if not main_content:
                    return "Could not find the article content."
                
                # Get all paragraphs
                paragraphs = main_content.find_all("p")
                
                # Extract text from paragraphs
                content_paragraphs = []
                for p in paragraphs:
                    text = p.get_text(strip=True)
                    if text and len(text) > 10:
                        content_paragraphs.append(text)
                
                # Join with proper spacing
                content = "\n\n".join(content_paragraphs)
                
                # Limit content length
                if len(content) > 10000:
                    content = content[:10000] + "..."
                
                return content if content else "No content found in the article."
            
            elif response.status_code == 403:
                print(f"Attempt {attempt + 1}: Got 403 Forbidden for {url}")
                
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (attempt + 1)
                    print(f"Waiting {wait_time:.2f} seconds before retry...")
                    time.sleep(wait_time)
                
            else:
                return f"Failed to fetch the page at {url}. Status code: {response.status_code}"
                
        except requests.exceptions.Timeout:
            print(f"Attempt {attempt + 1}: Timeout for {url}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
        
        except Exception as e:
            print(f"Attempt {attempt + 1}: Error fetching URL {url}: {e}")
            if attempt < max_retries - 1:
                time.sleep(retry_delay * (attempt + 1))
    
    return f"Failed to fetch the page at {url} after {max_retries} attempts."

def scrape_custom_json(json_url, save_path):
    try:
        # Use a new session for this request
        temp_session = requests.Session()
        temp_session.headers.update({
            "User-Agent": random.choice(user_agents),
            "Accept": "application/json, text/plain, */*",
        })
        
        response = temp_session.get(json_url, timeout=10)
        
        if response.status_code == 200:
            news_data = response.json()
            news_articles = news_data.get("news", [])[:5]  # Limit to 5 articles
            output_data = {"news": []}
            
            successful_scrapes = 0
            failed_scrapes = 0
            
            for i, news in enumerate(news_articles):
                title = news.get("title", "")
                href = news.get("href", "")
                
                if href:
                    print(f"Scraping article {i+1}/{len(news_articles)}: {title[:50]}...")
                    
                    # Add variable delay between requests
                    delay = random.uniform(3, 6)
                    time.sleep(delay)
                    
                    content = scrape_custom_content(href)
                    
                    # Check if scraping was successful
                    if "Failed to fetch" not in content and "Error" not in content:
                        successful_scrapes += 1
                    else:
                        failed_scrapes += 1
                        print(f"Warning: Could not scrape content for: {title}")
                    
                    output_data["news"].append({
                        "title": title,
                        "href": href,
                        "content": content,
                        "time": datetime.now(pytz.timezone("Africa/Harare")).strftime('%H:%M'),
                        "date": datetime.now(pytz.timezone("Africa/Harare")).strftime('%d %b %Y')
                    })
            
            print(f"Scraping complete: {successful_scrapes} successful, {failed_scrapes} failed")
            
            # Save to GitHub
            success = save_to_github(save_path, output_data)
            
            if success:
                return {
                    "message": f"Scraping complete for {json_url}.",
                    "articles_scraped": len(output_data["news"]),
                    "successful": successful_scrapes,
                    "failed": failed_scrapes
                }
            else:
                return {"error": "Failed to save data to GitHub."}
        else:
            return {"error": f"Failed to fetch the JSON file. Status code: {response.status_code}"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}

@app.route('/scrape/<feed_name>', methods=['GET'])
def scrape_feed(feed_name):
    if feed_name in feeds:
        feed_data = feeds[feed_name]
        success = scrape_and_save_to_github(
            rss_url=feed_data["rss_url"],
            content_class=feed_data["content_class"],
            image_class=feed_data.get("image_class"),
            json_file=feed_data["json_file"],
            custom_image_url=feed_data.get("custom_image_url"),
            site_headers=feed_data.get("headers")
        )
        if success:
            return jsonify({"message": f"Scraping completed for {feed_name}!"}), 200
        else:
            return jsonify({"error": f"Failed to scrape {feed_name}"}), 500
    else:
        return jsonify({"error": "Feed not found"}), 404

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
            success = save_to_github(json_file, {"news": data})
            if success:
                return jsonify({"message": f"Scraped {len(data)} articles for {category} and saved to GitHub."}), 200
            else:
                return jsonify({"error": f"Failed to save {category} data to GitHub."}), 500
        else:
            return jsonify({"error": f"Failed to scrape {category}."}), 500
    else:
        return jsonify({"error": "Category not found"}), 404

@app.route('/scrape/all', methods=['GET'])
def scrape_all():
    """Endpoint to scrape all feeds at once"""
    results = {}
    for feed_name in feeds:
        try:
            feed_data = feeds[feed_name]
            success = scrape_and_save_to_github(
                rss_url=feed_data["rss_url"],
                content_class=feed_data["content_class"],
                image_class=feed_data.get("image_class"),
                json_file=feed_data["json_file"],
                custom_image_url=feed_data.get("custom_image_url"),
                site_headers=feed_data.get("headers"),
                max_articles=5  # Limit for all scrape
            )
            results[feed_name] = "Success" if success else "Failed"
            # Add delay between different feeds
            time.sleep(random.uniform(5, 10))
        except Exception as e:
            results[feed_name] = f"Error: {str(e)}"
    
    return jsonify({"message": "Scraping all feeds completed", "results": results}), 200

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint"""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()}), 200

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
