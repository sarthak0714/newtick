from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import (
    TimeoutException,
    NoSuchElementException,
    StaleElementReferenceException,
)
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
import time
import json
import random
import undetected_chromedriver as uc
import requests
import re


class BrowserManager:
    """Manages browser initialization and common browser operations"""

    @staticmethod
    def get_random_user_agent():
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
        ]
        return random.choice(user_agents)

    @staticmethod
    def get_chrome_options():
        options = uc.ChromeOptions()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-infobars")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--start-maximized")
        options.add_argument(f"user-agent={BrowserManager.get_random_user_agent()}")
        return options

    @staticmethod
    def random_sleep(min_seconds=2, max_seconds=5):
        time.sleep(random.uniform(min_seconds, max_seconds))

    @staticmethod
    def scroll_page(driver):
        total_height = int(driver.execute_script("return document.body.scrollHeight"))
        for i in range(1, total_height, random.randint(100, 300)):
            driver.execute_script(f"window.scrollTo(0, {i});")
            time.sleep(random.uniform(0.1, 0.3))

    @staticmethod
    def wait_for_page_load(driver, timeout=30):
        try:
            WebDriverWait(driver, timeout).until(
                lambda d: d.execute_script("return document.readyState") == "complete"
            )
            BrowserManager.random_sleep(3, 6)
        except Exception as e:
            print(f"Warning: Page load wait timed out: {e}")

    @staticmethod
    def retry_on_failure(func, max_retries=3, delay=5):
        for attempt in range(max_retries):
            try:
                return func()
            except Exception as e:
                if attempt == max_retries - 1:
                    raise e
                print(
                    f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds..."
                )
                time.sleep(delay)


class BSEScraper:
    """Handles scraping of BSE website"""

    def __init__(self):
        self.url = "https://www.bseindia.com/corporates/Comp_Name.aspx"
        self.driver = None

    def init_browser(self):
        self.driver = uc.Chrome(options=BrowserManager.get_chrome_options())

    def check_for_error_page(self):
        try:
            error_text = self.driver.find_element(By.TAG_NAME, "body").text
            return "An error occurred while processing your request" in error_text
        except:
            return False

    def get_total_pages(self):
        try:
            pagination_info = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, "td[align='left'][colspan='4']")
                )
            )
            text = pagination_info.text
            match = re.search(r"of\s+(\d+)", text)
            if match:
                return int(match.group(1))
            return 1
        except Exception as e:
            print(f"Error getting total pages: {e}")
            return 1

    def extract_page_data(self):
        WebDriverWait(self.driver, 30).until(
            EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gvData"))
        )
        BrowserManager.scroll_page(self.driver)

        rows = self.driver.find_elements(
            By.CSS_SELECTOR, "#ContentPlaceHolder1_gvData tr:not(.pgr):not(.TTHeader)"
        )
        print(f"Found {len(rows)} rows on current page")

        page_data = []
        for row in rows:
            try:
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) >= 4:
                    entry = {
                        "security_code": cells[0].text.strip(),
                        "old_name": cells[1].text.strip(),
                        "new_name": cells[2].text.strip(),
                        "date": cells[3].text.strip(),
                    }
                    page_data.append(entry)
            except StaleElementReferenceException:
                print("Stale element encountered, retrying...")
                continue

        return page_data

    def navigate_to_next_page(self, current_page, total_pages):
        if current_page < total_pages:
            pagination_row = self.driver.find_elements(
                By.CSS_SELECTOR, "#ContentPlaceHolder1_gvData tr.pgr td table tr td"
            )
            page_links = []
            for cell in pagination_row:
                link = cell.find_elements(By.TAG_NAME, "a")
                if link:
                    page_links.append(link[0])

            next_link = page_links[current_page - 1]
            self.driver.execute_script("arguments[0].click();", next_link)
            print(f"Clicked page {current_page + 1}, waiting for load...")
            BrowserManager.random_sleep(4, 7)
            BrowserManager.wait_for_page_load(self.driver)
            BrowserManager.scroll_page(self.driver)
            return True
        return False

    def scrape(self):
        try:
            self.init_browser()
            today = datetime.now().strftime("%d %b %Y")
            current_year = datetime.now().year

            print(f"Navigating to {self.url}...")
            self.driver.get(self.url)
            BrowserManager.wait_for_page_load(self.driver)
            BrowserManager.scroll_page(self.driver)

            if self.check_for_error_page():
                print("Got error page, retrying with new session...")
                self.driver.quit()
                return self.scrape()

            # Select year and submit
            year_dropdown = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlYear"))
            )
            select = Select(year_dropdown)
            select.select_by_value(str(current_year))
            print(f"Selected year: {current_year}")

            BrowserManager.random_sleep(2, 4)

            submit_button = WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnSubmit"))
            )
            self.driver.execute_script("arguments[0].click();", submit_button)

            BrowserManager.random_sleep(8, 12)
            BrowserManager.wait_for_page_load(self.driver)
            BrowserManager.scroll_page(self.driver)

            if self.check_for_error_page():
                print("Got error page after submit, retrying with new session...")
                self.driver.quit()
                return self.scrape()

            WebDriverWait(self.driver, 60).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gvData"))
            )

            total_pages = self.get_total_pages()
            print(f"Total pages to process: {total_pages}")

            all_data = []
            page_num = 1

            while page_num <= total_pages:
                try:
                    page_data = BrowserManager.retry_on_failure(self.extract_page_data)
                    all_data.extend(page_data)

                    if not self.navigate_to_next_page(page_num, total_pages):
                        break

                    page_num += 1
                    print(f"Navigating to page {page_num} of {total_pages}")

                except Exception as e:
                    print(f"Error processing page {page_num}: {e}")
                    break

            return all_data

        except Exception as e:
            print(f"An error occurred: {e}")
            return []
        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass


class NSEScraper:
    """Handles scraping of NSE website"""

    def __init__(self):
        self.driver = None

    def init_browser(self):
        self.driver = uc.Chrome(options=BrowserManager.get_chrome_options())
        print("Initializing NSE session...")
        self.driver.get("https://www.nseindia.com")
        BrowserManager.wait_for_page_load(self.driver)
        BrowserManager.random_sleep(3, 5)

    def get_symbol(self, company_name):
        try:
            search_url = f"https://www.nseindia.com/api/search?q={company_name}&page=1&type=quotes"
            cookies = self.driver.get_cookies()
            cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

            headers = {
                "User-Agent": self.driver.execute_script("return navigator.userAgent"),
                "Accept": "application/json",
                "Accept-Language": "en-US,en;q=0.9",
                "Referer": "https://www.nseindia.com/",
                "Origin": "https://www.nseindia.com",
            }

            session = requests.Session()
            for cookie in cookies:
                session.cookies.set(cookie["name"], cookie["value"])

            response = session.get(search_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            for result in data.get("results", []):
                if result.get("symbol_info", "").lower() == company_name.lower():
                    url = result.get("url", "")
                    symbol_match = re.search(r"symbol=([^&]+)", url)
                    if symbol_match:
                        return symbol_match.group(1)

            return None
        except Exception as e:
            print(f"Error searching NSE for {company_name}: {e}")
            return None

    def process_entries(self, entries):
        try:
            self.init_browser()
            processed_entries = []

            for entry in entries:
                new_name = entry["new_name"]
                print(f"\nSearching NSE for: {new_name}")

                ticker = self.get_symbol(new_name)
                entry["ticker"] = ticker
                processed_entries.append(entry)

                BrowserManager.random_sleep(2, 4)

                if random.random() < 0.2:
                    print("Refreshing NSE session...")
                    self.driver.get("https://www.nseindia.com")
                    BrowserManager.wait_for_page_load(self.driver)
                    BrowserManager.random_sleep(3, 5)

            return processed_entries

        finally:
            if self.driver:
                try:
                    self.driver.quit()
                except:
                    pass


class NewTickerScraper:
    """Main class to orchestrate the scraping process"""

    def __init__(self):
        self.bse_scraper = BSEScraper()
        self.nse_scraper = NSEScraper()

    def run(self):
        # Scrape BSE data
        all_data = self.bse_scraper.scrape()
        if not all_data:
            print("No data scraped from BSE")
            return

        # Filter for today's entries
        today = datetime.now().strftime("%d %b %Y")
        today_entries = [entry for entry in all_data if entry["date"] == today]

        if today_entries:
            print(
                f"\nFound {len(today_entries)} company name changes for today ({today}):"
            )
            for entry in today_entries:
                print(
                    f"\nSecurity Code: {entry['security_code']}\nOld Name: {entry['old_name']}\nNew Name: {entry['new_name']}\nDate: {entry['date']}"
                )

            # Process NSE data for today's entries
            print("\nProcessing NSE data for today's entries...")
            processed_entries = self.nse_scraper.process_entries(today_entries)

            # Update all_data with NSE symbols
            for entry in all_data:
                if entry["date"] == today:
                    matching_entry = next(
                        (
                            e
                            for e in processed_entries
                            if e["security_code"] == entry["security_code"]
                        ),
                        None,
                    )
                    if matching_entry:
                        entry["ticker"] = matching_entry["ticker"]
        else:
            print(f"\nNo company name changes found for today ({today})")

        # Save to JSON
        with open("bse_name_changes.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\nAll scraped data has been saved to bse_name_changes.json")


if __name__ == "__main__":
    scraper = NewTickerScraper()
    scraper.run()
