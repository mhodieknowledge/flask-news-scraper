from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import html
import random

app = Flask(__name__)

# List of user agents for rotation
user_agents = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/79.0.3945.88 Safari/537.36",
    "Mozilla/5.0 (X11; Ubuntu; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/83.0.4103.97 Safari/537.36",
    "Mozilla/5.0 (Windows NT 6.1; WOW64; rv:24.0) Gecko/20100101 Firefox/24.0",
    "Mozilla/5.0 (Windows NT 6.1; rv:10.0) Gecko/20100101 Firefox/10.0",
    "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/64.0.3282.140 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14.4; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (X11; Linux i686; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36 Edg/123.0.2420.81"
    # Add more user agents here as needed
]

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    # Pick a random user agent from the list
    headers = {
        "User-Agent": random.choice(user_agents)
    }

    try:
        response = requests.get(url, headers=headers)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            
            # Find the div with class "post_data"
            post_data_div = soup.find("div", class_="page-content")
            if not post_data_div:
                return jsonify({"error": "No content found in the specified div"}), 404

            # Extract paragraphs from the div
            paragraphs = post_data_div.find_all("p")
            
            # Process paragraphs to remove Unicode and ensure proper formatting
            processed_paragraphs = []
            for p in paragraphs:
                # Remove Unicode characters and decode HTML entities
                clean_text = html.unescape(p.get_text(strip=True))
                
                # Remove non-printable characters
                clean_text = re.sub(r'[^\x20-\x7E\n]', '', clean_text)
                
                if clean_text:
                    processed_paragraphs.append(clean_text)

            # Join paragraphs with a blank line after each paragraph
            main_content = "\n\n".join(processed_paragraphs) + "\n\n"

            return jsonify({"content": main_content}), 200
        else:
            return jsonify({"error": f"Failed to fetch the page. Status code: {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
