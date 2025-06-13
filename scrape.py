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


def random_sleep(min_seconds=2, max_seconds=5):
    """Sleep for a random amount of time to simulate human behavior"""
    time.sleep(random.uniform(min_seconds, max_seconds))


def scroll_page(driver):
    """Scroll the page to simulate human behavior"""
    total_height = int(driver.execute_script("return document.body.scrollHeight"))
    for i in range(1, total_height, random.randint(100, 300)):
        driver.execute_script(f"window.scrollTo(0, {i});")
        time.sleep(random.uniform(0.1, 0.3))


def wait_for_page_load(driver, timeout=30):
    """Wait for the page to be fully loaded"""
    try:
        # Wait for document.readyState to be 'complete'
        WebDriverWait(driver, timeout).until(
            lambda d: d.execute_script("return document.readyState") == "complete"
        )
        # Additional wait for any loading indicators
        random_sleep(3, 6)
    except Exception as e:
        print(f"Warning: Page load wait timed out: {e}")


def retry_on_failure(func, max_retries=3, delay=5):
    """Retry a function if it fails"""
    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            print(f"Attempt {attempt + 1} failed: {e}. Retrying in {delay} seconds...")
            time.sleep(delay)


def check_for_error_page(driver):
    """Check if we've been redirected to an error page"""
    try:
        error_text = driver.find_element(By.TAG_NAME, "body").text
        return "An error occurred while processing your request" in error_text
    except:
        return False


def get_nse_symbol(driver, company_name):
    """Search NSE for company symbol using the company name"""
    try:
        # Format the search URL
        search_url = (
            f"https://www.nseindia.com/api/search?q={company_name}&page=1&type=quotes"
        )

        # Get cookies from the current session
        cookies = driver.get_cookies()

        # Convert cookies to requests format
        cookie_dict = {cookie["name"]: cookie["value"] for cookie in cookies}

        # Set up headers to mimic browser
        headers = {
            "User-Agent": driver.execute_script("return navigator.userAgent"),
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://www.nseindia.com/",
            "Origin": "https://www.nseindia.com",
        }

        # Make the request with cookies
        session = requests.Session()
        for cookie in cookies:
            session.cookies.set(cookie["name"], cookie["value"])

        response = session.get(search_url, headers=headers)
        response.raise_for_status()

        # Parse the response
        data = response.json()

        # Look for exact match in results
        for result in data.get("results", []):
            if result.get("symbol_info", "").lower() == company_name.lower():
                # Extract symbol from URL
                url = result.get("url", "")
                symbol_match = re.search(r"symbol=([^&]+)", url)
                if symbol_match:
                    return symbol_match.group(1)

        return None
    except Exception as e:
        print(f"Error searching NSE for {company_name}: {e}")
        return None


def init_nse_browser():
    """Initialize a new browser session for NSE"""
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    # Add random user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    driver = uc.Chrome(options=options)

    # Visit NSE homepage first to get cookies
    print("Initializing NSE session...")
    driver.get("https://www.nseindia.com")
    wait_for_page_load(driver)
    random_sleep(3, 5)

    return driver


def process_nse_data(bse_data):
    """Process BSE data and add NSE symbols for today's entries"""
    print("\nProcessing NSE data for companies...")
    processed_data = []

    # Get today's date in the required format
    today = datetime.now().strftime("%d %b %Y")
    print(f"Processing entries for today: {today}")

    # Filter data for today's entries
    filtered_data = [entry for entry in bse_data if entry["date"] == today]
    if not filtered_data:
        print(f"No entries found for today ({today})")
        return bse_data
    print(f"Found {len(filtered_data)} entries for today")

    # Initialize NSE browser
    driver = init_nse_browser()

    try:
        for entry in filtered_data:
            new_name = entry["new_name"]
            print(f"\nSearching NSE for: {new_name}")

            # Get NSE symbol
            nse_symbol = get_nse_symbol(driver, new_name)

            # Add NSE symbol to entry
            entry["nse_symbol"] = nse_symbol
            processed_data.append(entry)

            # Add delay between requests
            random_sleep(2, 4)

            # Refresh NSE homepage periodically to maintain session
            if random.random() < 0.2:  # 20% chance to refresh
                print("Refreshing NSE session...")
                driver.get("https://www.nseindia.com")
                wait_for_page_load(driver)
                random_sleep(3, 5)

    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass  # Ignore cleanup errors

    # Create a map of processed entries by security code
    processed_map = {entry["security_code"]: entry for entry in processed_data}

    # Update original data with processed entries
    for entry in bse_data:
        if entry["security_code"] in processed_map:
            entry["nse_symbol"] = processed_map[entry["security_code"]]["nse_symbol"]

    return bse_data


def get_total_pages(driver):
    """Get total number of pages from pagination element"""
    try:
        # Wait for pagination info to be present
        pagination_info = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "td[align='left'][colspan='4']")
            )
        )

        # Extract total pages from text
        text = pagination_info.text
        match = re.search(r"of\s+(\d+)", text)
        if match:
            return int(match.group(1))
        return 1
    except Exception as e:
        print(f"Error getting total pages: {e}")
        return 1


def scrape(url: str):
    # Set up Chrome options with more realistic browser behavior
    options = uc.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-infobars")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--start-maximized")

    # Add random user agent
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    ]
    options.add_argument(f"user-agent={random.choice(user_agents)}")

    driver = None
    try:
        driver = uc.Chrome(options=options)

        today = datetime.now().strftime("%d %b %Y")
        current_year = datetime.now().year

        print(f"Navigating to {url}...")
        driver.get(url)
        wait_for_page_load(driver)
        scroll_page(driver)

        if check_for_error_page(driver):
            print("Got error page, retrying with new session...")
            driver.quit()
            return scrape(url)  # Retry with new session

        print("Looking for year dropdown...")
        try:
            # Wait for the year dropdown to be present and clickable
            year_dropdown = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_ddlYear"))
            )
            print("Found year dropdown")

            # Select current year from dropdown
            select = Select(year_dropdown)
            select.select_by_value(str(current_year))
            print(f"Selected year: {current_year}")

            random_sleep(2, 4)

            print("Looking for submit button...")
            # Wait for submit button to be clickable and click it using JavaScript
            submit_button = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_btnSubmit"))
            )
            print("Found submit button, clicking...")
            driver.execute_script("arguments[0].click();", submit_button)

            # Wait longer after clicking submit
            print("Waiting for response after submit...")
            random_sleep(8, 12)
            wait_for_page_load(driver)
            scroll_page(driver)

            if check_for_error_page(driver):
                print("Got error page after submit, retrying with new session...")
                driver.quit()
                return scrape(url)  # Retry with new session

            print("Waiting for table to load...")
            # Wait for the table to load after submission with a longer timeout
            WebDriverWait(driver, 60).until(
                EC.presence_of_element_located((By.ID, "ContentPlaceHolder1_gvData"))
            )
            print("Table loaded successfully")

            # Get total number of pages
            total_pages = get_total_pages(driver)
            print(f"Total pages to process: {total_pages}")

        except TimeoutException as e:
            print(f"Timeout waiting for element: {e}")
            print("Current page source:")
            print(driver.page_source[:1000])
            if check_for_error_page(driver):
                print("Got error page, retrying with new session...")
                driver.quit()
                return scrape(url)  # Retry with new session
            return
        except Exception as e:
            print(f"Error during form submission: {e}")
            return

        all_data = []
        page_num = 1

        while page_num <= total_pages:
            try:

                def extract_page_data():
                    # Wait for the table to load
                    WebDriverWait(driver, 30).until(
                        EC.presence_of_element_located(
                            (By.ID, "ContentPlaceHolder1_gvData")
                        )
                    )

                    # Scroll to ensure all elements are loaded
                    scroll_page(driver)

                    # Get all rows except header and pagination
                    rows = driver.find_elements(
                        By.CSS_SELECTOR,
                        "#ContentPlaceHolder1_gvData tr:not(.pgr):not(.TTHeader)",
                    )
                    print(f"Found {len(rows)} rows on page {page_num} of {total_pages}")

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

                # Retry data extraction if it fails
                page_data = retry_on_failure(extract_page_data)
                all_data.extend(page_data)

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
                if page_num < total_pages:
                    try:
                        # Click the next page link (page_links[page_num] is the next page)
                        next_link = page_links[page_num - 1]  # 0-based index
                        driver.execute_script("arguments[0].click();", next_link)
                        print(f"Clicked page {page_num + 1}, waiting for load...")
                        random_sleep(4, 7)
                        wait_for_page_load(driver)
                        scroll_page(driver)
                        page_num += 1
                        print(f"Navigating to page {page_num} of {total_pages}")
                    except Exception as e:
                        print(f"Error navigating to next page: {e}")
                        break
                else:
                    print("No more pages to process")
                    break

            except Exception as e:
                print(f"Error processing page {page_num}: {e}")
                break

        # Filter for today's entries
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
            nse_driver = init_nse_browser()
            try:
                for entry in today_entries:
                    new_name = entry["new_name"]
                    print(f"\nSearching NSE for: {new_name}")

                    # Get NSE symbol
                    nse_symbol = get_nse_symbol(nse_driver, new_name)

                    # Add NSE symbol to entry
                    entry["ticker"] = nse_symbol

                    # Add delay between requests
                    random_sleep(2, 4)

                    # Refresh NSE homepage periodically to maintain session
                    if random.random() < 0.2:  # 20% chance to refresh
                        print("Refreshing NSE session...")
                        nse_driver.get("https://www.nseindia.com")
                        wait_for_page_load(nse_driver)
                        random_sleep(3, 5)
            finally:
                if nse_driver:
                    try:
                        nse_driver.quit()
                    except:
                        pass  # Ignore cleanup errors

            # Update all_data with NSE symbols
            for entry in all_data:
                if entry["date"] == today:
                    matching_entry = next(
                        (
                            e
                            for e in today_entries
                            if e["security_code"] == entry["security_code"]
                        ),
                        None,
                    )
                    if matching_entry:
                        entry["nse_symbol"] = matching_entry["nse_symbol"]
        else:
            print(f"\nNo company name changes found for today ({today})")

        # Dump all data to JSON
        with open("bse_name_changes.json", "w", encoding="utf-8") as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
        print(f"\nAll scraped data has been saved to bse_name_changes.json")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass  # Ignore cleanup errors


def process_specific_date(date_str):
    """Process NSE data for a specific date

    Args:
        date_str (str): Date in format "DD MMM YYYY" (e.g., "15 Mar 2024")
    """
    try:
        # Load existing data
        with open("bse_name_changes.json", "r", encoding="utf-8") as f:
            data = json.load(f)

        # Process NSE data for the specific date
        processed_data = process_nse_data(data)

        # Save updated data
        with open("bse_name_changes.json", "w", encoding="utf-8") as f:
            json.dump(processed_data, f, ensure_ascii=False, indent=2)

        print(
            f"\nUpdated NSE symbols for date {date_str} have been saved to bse_name_changes.json"
        )

    except FileNotFoundError:
        print("Error: bse_name_changes.json not found. Please run the scraper first.")
    except Exception as e:
        print(f"Error processing date {date_str}: {e}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        # If date is provided as argument, process that date
        date_str = sys.argv[1]
        process_specific_date(date_str)
    else:
        # Otherwise run the full scraper
        url = "https://www.bseindia.com/corporates/Comp_Name.aspx"
        scrape(url)
