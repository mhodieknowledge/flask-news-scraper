from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup
import re
import html

app = Flask(__name__)

@app.route('/scrape', methods=['GET'])
def scrape():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "URL is required"}), 400

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/117.0.0.0 Safari/537.36"
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
