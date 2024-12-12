import requests
import json
import os
import base64
from bs4 import BeautifulSoup

# GitHub configuration
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
REPO_OWNER = "zeroteq"  # Replace with your GitHub username
REPO_NAME = "flask-news-scraper"  # Replace with your repository name
BRANCH = "main"  # GitHub branch to use

def scrape_and_save_category(category, url, json_file):
    """Scrape a specific category page and save data to GitHub."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("div", class_="td-module-meta-info")

        # Extract title and link
        data = []
        for article in articles:
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category.capitalize():
                title = article.find("p", class_="entry-title td-module-title").find("a").text.strip()
                href = article.find("p", class_="entry-title td-module-title").find("a")["href"]
                data.append({"title": title, "href": href})

        # Save to GitHub
        save_to_github(json_file, {"news": data})
        print(f"Scraped {len(data)} articles for {category}. Data saved to GitHub.")
    else:
        print(f"Failed to fetch category: {category}. Status code: {response.status_code}")

def save_to_github(json_file, data):
    """Save the scraped data to GitHub."""
    file_content = json.dumps(data, indent=4)
    encoded_content = base64.b64encode(file_content.encode("utf-8")).decode("utf-8")

    # GitHub API URL for the file
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{json_file}?ref={BRANCH}"
    headers = {
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github.v3+json",
    }

    # Check if the file already exists
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        file_info = response.json()
        sha = file_info["sha"]
    else:
        sha = None  # File does not exist yet

    # Prepare the request payload
    payload = {
        "message": f"Update {json_file} with latest scraped articles",
        "content": encoded_content,
        "branch": BRANCH,
    }
    if sha:
        payload["sha"] = sha

    # Make the PUT request to save the file
    response = requests.put(url, headers=headers, json=payload)
    if response.status_code in (200, 201):
        print(f"{json_file} updated successfully on GitHub.")
    else:
        print(f"Failed to update {json_file} on GitHub: {response.status_code}, {response.text}")

if __name__ == "__main__":
    categories = {
        "business": "https://www.zbcnews.co.zw/category/business/",
        "local": "https://www.zbcnews.co.zw/category/local-news/",
        "sport": "https://www.zbcnews.co.zw/category/sport/",
    }
    json_files = {
        "business": "custom-rss/business.json",
        "local": "custom-rss/local.json",
        "sport": "custom-rss/sport.json",
    }

    # Scrape each category and save data
    for category, url in categories.items():
        scrape_and_save_category(category, url, json_files[category])
