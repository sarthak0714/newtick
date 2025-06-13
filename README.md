# NewTicker Scraper

A Python script that scrapes company name changes from BSE India and matches them with their NSE ticker symbols.

## Features

- Scrapes company name changes from BSE India website
- Automatically matches companies with their NSE ticker symbols
- Saves data in JSON format with security codes, old names, new names, and NSE tickers
- Handles pagination and anti-bot measures
- Uses undetected-chromedriver for better scraping reliability

## Requirements

```bash
pip install selenium undetected-chromedriver requests webdriver-manager
```

## Usage

```python
from scrape import NewTickerScraper

scraper = NewTickerScraper()
scraper.run()
```

The script will:

1. Scrape all company name changes from BSE
2. Filter for today's entries
3. Find matching NSE ticker symbols
4. Save results to `bse_name_changes.json`

## Output Format

```json
[
  {
    "security_code": "500325",
    "old_name": "Old Company Name",
    "new_name": "New Company Name",
    "date": "15 Mar 2024",
    "ticker": "NSE_SYMBOL"
  }
]
```
