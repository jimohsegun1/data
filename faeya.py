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
BASE_URL = "https://fa-eyau-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs"
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
def scrape_faeya_jobs():
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

        driver.get(BASE_URL )
        time.sleep(random.uniform(2, 4))

        for keyword in SEARCH_KEYWORDS:
            driver.get(BASE_URL)
            wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="keyword"]')))
            log_and_print("🌐 input found.")
            time.sleep(random.uniform(2, 4))


            try:
                log_and_print(f"🔎 Starting search for keyword: '{keyword}'")

                # Locate and click into the search input
                search_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="keyword"]')))
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
                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div/div/div/div/div[3]/div/div/div/div[2]/div/div/ul')))
                log_and_print("🔍 Search results loaded.")



                # Wait for job list to load
                ul_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-list__list")))

                # Get all job cards (li elements)
                job_items = ul_element.find_elements(By.CSS_SELECTOR, "li[data-qa='searchResultItem']")

                log_and_print(f"📌 Found {len(job_items)} job(s) on the page.")

                # Extract job title and URL
                for idx, job in enumerate(job_items, 1):
                    try:
                        # Extract job URL
                        job_link = job.find_element(By.CSS_SELECTOR, "a.job-list-item__link")
                        job_url = job_link.get_attribute("href").strip()

                        # Extract job title
                        job_title_el = job.find_element(By.CSS_SELECTOR, "span.job-tile__title")
                        job_title = job_title_el.text.strip()

                        log_and_print(f"🔗 Job {idx}: {job_title} — {job_url}")

                    
                    except Exception as e:
                        log_and_print(f"⚠️ Error parsing job item {idx}: {e}")


                



            except TimeoutException:
                log_and_print(f"❌ Failed to load results for keyword: {keyword}")
                continue


            




        # ==========================
        # # # Save to CSV
        # if all_data:
        #     os.makedirs("data", exist_ok=True)
        #     filename = f"data/faeya_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
    scrape_faeya_jobs()
