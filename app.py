import requests
import random
import html
import re
import feedparser
import json
import os
from git import Repo

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
    
    # Instead of saving to a file, we'll commit and push the changes to GitHub
    repo = Repo(".")
    with open("news.json", "w") as json_file:
        json.dump(news_content, json_file, indent=4)

    # Commit and push the changes to GitHub
    repo.git.add("news.json")
    repo.index.commit("Update news.json with latest scraped articles")

    # Get GitHub token from environment variables
    github_token = os.getenv("GITHUB_TOKEN")
    repo.git.push("https://x-access-token:" + github_token + "@github.com/YOUR_USERNAME/YOUR_REPOSITORY.git", "main")

    print("News data saved successfully and pushed to GitHub")

# Example RSS feed URL
rss_url = "https://www.zimeye.net/feed/"
scrape_and_save(rss_url)
