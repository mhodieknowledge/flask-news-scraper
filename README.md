# Zimbabwe News Scraper

A comprehensive news aggregation backend that scrapes news from major Zimbabwean news outlets and stores the content in a GitHub repository.

## Features

- **Multi-Source Aggregation**: Scrapes news from Chronicle, NewZimbabwe, ZimEye, Herald, and ZBC
- **Category Support**: Extracts news by categories (Business, Local News, Sports)
- **Automated Content Extraction**: Pulls full article content, images, and metadata
- **GitHub Integration**: Automatically stores scraped data in JSON format to your GitHub repository
- **RESTful API**: Simple endpoints to trigger scraping operations
- **User-Agent Rotation**: Prevents blocking by rotating between different user agents

## Installation

1. Clone the repository:
```bash
git clone https://github.com/zeroteq/flask-news-scraper.git
cd flask-news-scraper
```

2. Install required dependencies:
```bash
pip install flask requests beautifulsoup4 feedparser pytz
```

3. Set up GitHub authentication:
```bash
export GITHUB_TOKEN=your_github_personal_access_token
```

## Configuration

The application is configured to work with the following news sources:
- Chronicle (`https://www.chronicle.co.zw/feed/`)
- NewZimbabwe (`https://www.newzimbabwe.com/feed/`)
- ZimEye (`https://www.zimeye.net/feed/`)
- Herald (`https://www.herald.co.zw/feed/`)
- ZBC News (by categories)

To add or modify sources, edit the `feeds` and `categories` dictionaries in `main.py`.

## Usage

1. Start the Flask server:
```bash
python main.py
```

2. Trigger scraping operations using the API endpoints:

- Scrape a specific news source:
```
GET /scrape/{feed_name}
```
Where `{feed_name}` is one of: `chronicle`, `newzimbabwe`, `zimeye`, or `herald`

- Scrape a specific category from ZBC:
```
GET /scrape/category/{category}
```
Where `{category}` is one of: `business`, `local-news`, or `sport`

- Scrape custom JSON sources:
```
GET /scrape/custom/{category}
```
Where `{category}` is one of: `business`, `local-news`, or `sport`

## Data Structure

The scraped data is stored in JSON files with the following structure:

```json
{
  "news": [
    {
      "title": "Article Title",
      "url": "https://article-url.com",
      "content": "Full article content...",
      "image_url": "https://image-url.com/image.jpg",
      "description": "Article description or summary",
      "time": "14:30",
      "date": "10 Nov 2023"
    },
    // more articles...
  ]
}
```

## Repository Structure

- `news/`: JSON files for individual news sources
- `custom-rss/`: Category-specific JSON files
- `zbc/`: Processed ZBC category articles

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
