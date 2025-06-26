import traceback
import sys
import gc
import os
import re
import time
import json
import hashlib
import logging
import random
import pandas as pd
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import NoSuchElementException, TimeoutException, StaleElementReferenceException
import undetected_chromedriver as uc


# --- Configuration ---
RUN_HEADLESS = True
SEARCH_KEYWORDS = ["Microsoft Dynamics", "Power Platform"]


# --- Setup logging ---
if not os.path.exists("log"):
    os.makedirs("log")
log_file = os.path.join("log", "rsm_scrape.log")


logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def log_and_print(message):
    print(message)
    logging.info(message)


def hash_job(job):
    return hashlib.md5(json.dumps(job, sort_keys=True).encode()).hexdigest()


# --- Scraper Logic ---
def scrape_rsm_jobs():
    start_time = datetime.now()
    log_and_print(f"\n🚀 Scraping started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")


    options = webdriver.ChromeOptions()
    if RUN_HEADLESS:
        options.add_argument("--headless=new")
    options.add_argument("--disable-blink-features=AutomationControlled")    
    options.add_argument("--ignore-certificate-errors")
    options.add_argument("--ignore-ssl-errors")
    # options.add_argument("--disable-javascript")
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )


    driver = None
    try:
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 15)


        all_data = []

        driver.get("https://rsm.wd1.myworkdayjobs.com/en-US/RSMCareers")
        time.sleep(random.uniform(2, 4))

        for keyword in SEARCH_KEYWORDS:
            driver.get("https://rsm.wd1.myworkdayjobs.com/en-US/RSMCareers")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-automation-id='keywordSearchSection']")))
            time.sleep(random.uniform(2, 4))


            try:
                log_and_print(f"🔎 Starting search for keyword: '{keyword}'")

                # Locate and click into the search input
                search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[data-automation-id='keywordSearchInput']")))
                log_and_print("✅ Search input located.")

                # Simulate human-like interaction
                ActionChains(driver).move_to_element(search_input).click().perform()
                time.sleep(random.uniform(0.5, 1.5))

                search_input.send_keys(Keys.CONTROL + "a")
                search_input.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(1, 2))

                search_input.send_keys(keyword)
                time.sleep(random.uniform(0.5, 1.5))
                search_input.send_keys(Keys.RETURN)

                log_and_print("🔘 Search input submitted.")
                time.sleep(random.uniform(3, 5))

                # Confirm search results loaded
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "p[data-automation-id='jobFoundText']")))
                log_and_print("🔍 Search results loaded.")

            except TimeoutException:
                log_and_print(f"❌ Failed to load results for keyword: {keyword}")
                continue


            page = 1
            prev_card_count = -1

            while True:
                log_and_print(f"📄 Processing page {page} for keyword '{keyword}'")

                try:
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, "section[data-automation-id='jobResults'] > ul[role='list'] > li.css-1q2dra3")))
                    job_cards = driver.find_elements(By.CSS_SELECTOR, "section[data-automation-id='jobResults'] > ul[role='list'] > li.css-1q2dra3")
                    log_and_print(f"🔢 Found {len(job_cards)} job cards on page {page}")
                except TimeoutException:
                    log_and_print("⚠️ No job cards found.")
                    break


                first_card = job_cards[0]

                # Try clicking next and waiting for the first card to go stale (indicating page change)
                try:
                    next_button = driver.find_element(By.CSS_SELECTOR, "button[aria-label='next']")
                    if next_button.is_enabled() and "disabled" not in next_button.get_attribute("class"):
                        next_button.click()
                        wait.until(EC.staleness_of(first_card))  # Ensures new content is loaded
                        page += 1
                        time.sleep(2)
                    else:
                        log_and_print("⛔ Reached last page or pagination not available.")
                        break
                except NoSuchElementException:
                    log_and_print("ℹ️ No pagination button found, assuming single page.")
                    break

        # ==========================
        # # Save to CSV
        # if all_data:
        #     os.makedirs("data", exist_ok=True)
        #     filename = f"data/rsm_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        #     pd.DataFrame(all_data).to_csv(filename, index=False)
        #     log_and_print(f"📁 Data saved to {filename}")
        # else:
        #     log_and_print("⚠️ No data scraped.")


    except Exception as e:
        log_and_print(f"❌ Fatal error during scraping: {e}")
        log_and_print(traceback.format_exc())


    finally:
        if driver:
            driver.quit()
            gc.collect()  # Helps clean up remaining references
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        log_and_print(f"✅ Scraping finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Duration: {duration:.2f} seconds)")


# --- Main Execution Block ---
if __name__ == "__main__":
    scrape_rsm_jobs()