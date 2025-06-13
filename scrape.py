from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import json


def scrape(url: str):
    # Set up Chrome options
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")

    # Initialize the Chrome driver with webdriver-manager
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)

    try:
        # Get today's date in the format used by the website (e.g., "20 Jan 2024")
        today = datetime.now().strftime("%d %b %Y")

        # Navigate to the URL
        driver.get(url)

        all_data = []
        page_num = 1

        while True:
            # Wait for the table to load
            try:
                WebDriverWait(driver, 20).until(
                    EC.presence_of_element_located(
                        (By.ID, "ContentPlaceHolder1_gvData")
                    )
                )
            except Exception as e:
                print(f"Error waiting for table: {e}")
                break

            # Get all rows except header and pagination
            rows = driver.find_elements(
                By.CSS_SELECTOR,
                "#ContentPlaceHolder1_gvData tr:not(.pgr):not(.TTHeader)",
            )

            # Extract data from current page
            for row in rows:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    entry = {
                        "security_code": cells[0].text.strip(),
                        "old_name": cells[1].text.strip(),
                        "new_name": cells[2].text.strip(),
                        "date": cells[3].text.strip(),
                    }
                    all_data.append(entry)

            # Find pagination row and all page links
            pagination_row = driver.find_elements(
                By.CSS_SELECTOR, "#ContentPlaceHolder1_gvData tr.pgr td table tr td"
            )
            page_links = []
            for cell in pagination_row:
                link = cell.find_elements(By.TAG_NAME, "a")
                if link:
                    page_links.append(link[0])
                else:
                    # Current page is a <span>
                    span = cell.find_elements(By.TAG_NAME, "span")
                    if span:
                        current_page = span[0].text.strip()

            # If there is a next page, click it
            if page_num < len(page_links) + 1:
                try:
                    # Click the next page link (page_links[page_num] is the next page)
                    next_link = page_links[page_num - 1]  # 0-based index
                    driver.execute_script("arguments[0].click();", next_link)
                    time.sleep(2)
                    page_num += 1
                except Exception as e:
                    break
            else:
                break

        # Filter for today's entries
        today_entries = [entry for entry in all_data if entry["date"] == today]

        # Print today's entries
        if today_entries:
            print(
                f"\nFound {len(today_entries)} company name changes for today ({today}):"
            )
            for entry in today_entries:
                print(f"\nSecurity Code: {entry['security_code']}")
                print(f"Old Name: {entry['old_name']}")
                print(f"New Name: {entry['new_name']}")
                print(f"Date: {entry['date']}")
        else:
            print(f"\nNo company name changes found for today ({today})")

        # Dump all data to JSON
        with open("bse_name_changes.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\nAll scraped data has been saved to bse_name_changes.json")

    finally:
        driver.quit()


if __name__ == "__main__":
    url = "https://www.bseindia.com/corporates/Comp_Name.aspx"
    scrape(url)
