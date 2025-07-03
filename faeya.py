import traceback
import sys
import gc
import os
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
from selenium.common.exceptions import NoSuchElementException, TimeoutException
import undetected_chromedriver as uc

# --- Configuration ---
RUN_HEADLESS = True
BASE_URL = "https://fa-eyau-saasfaprod1.fa.ocs.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1/jobs"
SEARCH_KEYWORDS = ["Microsoft Dynamics", "Power Platform"]

# --- Logging Setup ---
os.makedirs("log", exist_ok=True)
log_file = os.path.join("log", "rsm_scrape.log")

logging.basicConfig(
    filename=log_file,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

def log_and_print(message):
    print(message)
    logging.info(message)

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
    options.add_argument("--disable-infobars")
    options.add_argument("--lang=en-US,en;q=0.9")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.5845.188 Safari/537.36"
    )

    driver = None
    try:
        driver = uc.Chrome(options=options)
        wait = WebDriverWait(driver, 15)
        all_links = []
        all_data = []

        driver.get(BASE_URL)
        time.sleep(random.uniform(2, 4))

        for keyword in SEARCH_KEYWORDS:
            driver.get(BASE_URL)
            wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="keyword"]')))
            log_and_print("🌐 Input field found.")
            time.sleep(random.uniform(2, 4))

            try:
                log_and_print(f"🔎 Starting search for keyword: '{keyword}'")
                search_input = wait.until(EC.element_to_be_clickable((By.XPATH, '//*[@id="keyword"]')))
                ActionChains(driver).move_to_element(search_input).click().perform()
                time.sleep(random.uniform(0.5, 1.5))

                search_input.send_keys(Keys.CONTROL + "a")
                search_input.send_keys(Keys.BACKSPACE)
                time.sleep(random.uniform(1, 2))
                search_input.send_keys(keyword)
                time.sleep(random.uniform(0.5, 1.5))
                search_input.send_keys(Keys.RETURN)

                log_and_print("🔘 Search submitted.")
                time.sleep(random.uniform(3, 5))

                wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="main"]/div/div/div/div/div/div[3]/div/div/div/div[2]/div/div/ul')))
                ul_element = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.jobs-list__list")))
                job_items = ul_element.find_elements(By.CSS_SELECTOR, "li[data-qa='searchResultItem']")

                log_and_print(f"📌 Found {len(job_items)} job(s) on the page.")

                for idx, job in enumerate(job_items, 1):
                    try:
                        job_link = job.find_element(By.CSS_SELECTOR, "a.job-list-item__link")
                        job_url = job_link.get_attribute("href").strip()
                        job_title = job.find_element(By.CSS_SELECTOR, "span.job-tile__title").text.strip()

                        all_links.append({
                            "url": job_url,
                            "title": job_title,
                            "keyword": keyword
                        })
                        log_and_print(f"🔗 Job {idx}: {job_title} — {job_url}")
                    except Exception as e:
                        log_and_print(f"⚠️ Error parsing job item {idx}: {e}")
            except TimeoutException:
                log_and_print(f"❌ Failed to load results for keyword: {keyword}")
                continue

        # --- Visit Detail Pages ---
        log_and_print(f"\n🔍 Visiting {len(all_links)} job detail page(s)...")

        for i, job_info in enumerate(all_links, 1):
            job_title = job_info["title"]
            job_url = job_info["url"]
            keyword = job_info["keyword"]

            log_and_print(f"\n🌐 Visiting job {i}: {job_title} — {job_url}")
            try:
                driver.get(job_url)
                time.sleep(random.uniform(2, 4))

                # --- Extract Description ---
                description = "N/A"
                try:
                    ul_elements = driver.find_elements(By.TAG_NAME, "ul")
                    if len(ul_elements) >= 4:
                        li_elements = ul_elements[3].find_elements(By.TAG_NAME, "li")
                        li_texts = [li.text.strip() for li in li_elements if li.text.strip()]
                        if li_texts:
                            description = " | ".join(li_texts)
                    log_and_print(f"📝 Description: {description}")
                except Exception as e:
                    log_and_print(f"⚠️ Failed to extract description UL: {e}")

                # --- Extract Job Metadata ---
                job_id = "N/A"
                role_type = "N/A"
                location = "N/A"
                salary = "N/A"
                level = "N/A"

                min_salary = None
                max_salary = None

                try:
                    meta_section = WebDriverWait(driver, 10).until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, "ul.job-meta__list"))
                    )
                    items = meta_section.find_elements(By.CSS_SELECTOR, "li.job-meta__item")

                    for item in items:
                        try:
                            title_span = item.find_element(By.CSS_SELECTOR, "span.job-meta__title")
                            value_span = item.find_element(By.CSS_SELECTOR, "span.job-meta__subitem")
                            title = title_span.text.strip()

                            if title == "Job Identification":
                                value = value_span.text.strip()
                                if value:
                                    job_id = value

                            elif title == "Job Category":
                                value = value_span.text.strip()
                                if value:
                                    role_type = value

                            elif title == "Locations":
                                locations = value_span.find_elements(By.CSS_SELECTOR, ".job-meta__pin-item")
                                location_list = [loc.text.strip() for loc in locations if loc.text.strip()]
                                workplace_type = ""
                                try:
                                    workplace_type_span = value_span.find_element(By.CSS_SELECTOR, ".job-meta__workplace-type")
                                    workplace_type = workplace_type_span.text.strip()
                                except:
                                    pass
                                if location_list:
                                    location = ", ".join(location_list)
                                    if workplace_type:
                                        location += f" {workplace_type}"

                            elif title == "Minimum Salary":
                                value = value_span.text.strip()
                                if value and value != ".":
                                    min_salary = value

                            elif title == "Maximum Salary":
                                value = value_span.text.strip()
                                if value and value != ".":
                                    max_salary = value

                        except Exception as e:
                            log_and_print(f"⚠️ Error parsing job meta item: {e}")

                    if min_salary and max_salary:
                        salary = f"{min_salary} - {max_salary}"
                    elif min_salary:
                        salary = min_salary
                    elif max_salary:
                        salary = max_salary

                    # Append job to final data
                    all_data.append({
                        "job_title": job_title,
                        "job_url": job_url,
                        "job_id": job_id,
                        "location": location,
                        "role_type": role_type,
                        "salary": salary,
                        "description": description,
                        "keyword": keyword,
                        "level": level
                    })

                    # Log each job summary
                    log_and_print(f"📌 Job ID: {job_id}")
                    log_and_print(f"📍 Location(s): {location}")
                    log_and_print(f"🧩 Role Type: {role_type}")
                    log_and_print(f"💰 Salary: {salary}")

                except TimeoutException:
                    log_and_print("❌ Failed to locate job metadata section.")
            except Exception as e:
                log_and_print(f"⚠️ Error visiting detail page for {job_title}: {e}")

        # --- Save Final Results ---
        if all_data:
            os.makedirs("data", exist_ok=True)
            filename = f"data/faeya_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(all_data).to_csv(filename, index=False)
            log_and_print(f"\n📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No job data to save.")

    except Exception as e:
        log_and_print(f"❌ Fatal error during scraping: {e}")
        log_and_print(traceback.format_exc())

    finally:
        if driver:
            driver.quit()
            gc.collect()
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        log_and_print(f"\n✅ Scraping finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')} (Duration: {duration:.2f} seconds)")

# --- Main Execution ---
if __name__ == "__main__":
    scrape_faeya_jobs()
