from flask import Flask, request, jsonify
import requests
from bs4 import BeautifulSoup

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
            main_content = "\n\n".join(p.get_text(strip=True) for p in paragraphs)

            return jsonify({"content": main_content}), 200
        else:
            return jsonify({"error": f"Failed to fetch the page. Status code: {response.status_code}"}), response.status_code
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True)
