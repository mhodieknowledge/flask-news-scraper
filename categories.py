import requests
import random
import json
import os
import base64
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

# GitHub configuration
github_token = os.getenv("GITHUB_TOKEN")
repo_owner = "zeroteq"  # Replace with your GitHub username
repo_name = "flask-news-scraper"  # Replace with your repository name
branch = "main"

# Category configuration
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

def scrape_category_page(url, category_name):
    """Scrape a specific category page for articles."""
    headers = {"User-Agent": random.choice(user_agents)}
    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        soup = BeautifulSoup(response.content, "html.parser")
        articles = soup.find_all("div", class_="td-module-meta-info")

        # Extract title and link
        data = []
        for article in articles:
            category_tag = article.find("a", class_="td-post-category")
            if category_tag and category_tag.text.strip() == category_name.capitalize():
                title = article.find("p", class_="entry-title td-module-title").find("a").text.strip()
                href = article.find("p", class_="entry-title td-module-title").find("a")["href"]
                data.append({"title": title, "href": href})
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
        sha = None  # File does not exist yet

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
    app.run(debug=True, port=5001)
