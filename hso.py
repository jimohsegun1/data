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
def scrape_hso_jobs():
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

        driver.get("https://www.hso.com/careers/vacancies/")
        time.sleep(random.uniform(2, 4))

        for keyword in SEARCH_KEYWORDS:
            driver.get("https://www.hso.com/careers/vacancies/")
            wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "input[name='searchTerm']")))
            time.sleep(random.uniform(2, 4))


            try:
                log_and_print(f"🔎 Starting search for keyword: '{keyword}'")

                # Locate and click into the search input
                search_input = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[name='searchTerm']")))
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
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "article[class='card card--text']")))
                log_and_print("🔍 Search results loaded.")

            except TimeoutException:
                log_and_print(f"❌ Failed to load results for keyword: {keyword}")
                continue


            page = 1

            while True:
                log_and_print(f"📄 Processing page {page} for keyword '{keyword}'")

                try:
                    wait.until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div.card--text__content')))
                    job_cards = driver.find_elements(By.CSS_SELECTOR, 'article.card.card--text')
                    log_and_print(f"🔢 Found {len(job_cards)} job cards on page {page}")
                except TimeoutException:
                    log_and_print("⚠️ No job cards found.")
                    break

                # Get details for each job card on the job list page
                for card in job_cards:
                    try:
                        title = card.find_element(By.CSS_SELECTOR, "h3.h4").text.strip()
                        url_el = card.find_element(By.CSS_SELECTOR, "a.btn.btn--line.btn--full")
                        job_url = url_el.get_attribute("href").strip()

            #           # --- Locationn ---
                        # ✅ Correct
                        location_tags = card.find_elements(By.CSS_SELECTOR, "div.text-tags__row--cyan span")
                        location = ", ".join([tag.text.strip() for tag in location_tags])
           


            #           # --- description ---  
                        description = card.find_element(By.CSS_SELECTOR, "p.line-clamp-5").text.strip()
                        
                        job_id = "N/A"
                        level = "N/A"

                            

                        job_data = {
                            "title": title,
                            "location": location,
                            "job_id": job_id,
                            "level": level,
                            "job_url": job_url,
                            "keyword": keyword,
                            "description": description
                        }
                        all_data.append(job_data)
                        log_and_print(f"✅ Scraped job: {title} | {location} | {job_id} | {level} | {job_url} | {keyword}")


            #             # Click job to go to detail page
            #             log_and_print(f"🖱️ Clicking job link: {title}")
            #             driver.execute_script("arguments[0].scrollIntoView(true);", url_el)
            #             url_el.click()

            #             # Wait for job detail content to load (adjust selector as needed)
            #             wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[aria-label='Job Posting Description'][tabindex='0']")))

            #             # Confirm we are on the right job page by logging header or job ID
            #             try:
            #                 job_header_el = driver.find_element(By.CSS_SELECTOR, "h2[data-automation-id='jobPostingHeader']")
            #                 job_header = job_header_el.text.strip()
            #                 log_and_print(f"📄 Opened job detail page for: {job_header}")

            #             except Exception as e:
            #                 log_and_print(f"⚠️ Could not confirm job detail page: {e}")

            #             # Location extraction
            #             try:
            #                 # Narrow the scope to ONLY inside the main job posting container
            #                 job_detail_section = driver.find_element(By.XPATH, '//*[@id="mainContent"]/div/div[2]/div/div/section/div/div[2]/div/div/div/div[1]/div/div[1]/div')
            #                 location_elements = job_detail_section.find_elements(By.CSS_SELECTOR, "div[data-automation-id='locations'] dd")

            #                 # Strip and clean only non-empty values
            #                 location_list = [el.text.strip() for el in location_elements if el.text.strip()]
                            
            #                 if location_list:
            #                     location = ", ".join(location_list)
            #                     log_and_print(f"📍 Location(s) found: {location}")
            #                 else:
            #                     location = "Unknown"
            #                     log_and_print("⚠️ No location text found.")
            #             except Exception as e:
            #                 location = "Unknown"
            #                 log_and_print(f"⚠️ Error getting locations: {e}")


            #             # Description extraction
            #             try:
            #                 description_el = driver.find_element(By.XPATH, '//*[@id="mainContent"]/div/div[2]/div/div/section/div/div[2]/div/div/div/div[2]/div/div/p[1]')
            #                 description = description_el.text.strip()
            #                 log_and_print(f"📝 Description found: {description[:100]}...")  # Only show first 100 chars
            #             except Exception as e:
            #                 description = "Not found"
            #                 log_and_print(f"⚠️ Could not extract job description: {e}")


            #             job_data["location"] = location
            #             job_data["description"] = description

            #             all_data.append(job_data)
            #             # log_and_print(f"✅ Scraped full job data: {job_data}")




            #             # Go back to job list
            #             driver.back()
            #             wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "section[data-automation-id='jobResults'] ul[role='list'] > li.css-1q2dra3")))
            #             time.sleep(2) 

                    except Exception as e:
                        log_and_print(f"⚠️ Error extracting job card: {e}")
                        continue

                first_card = job_cards[0]


                try:
                    # Find the NEXT (right) arrow button — the last circle-arrow (non-rotated)
                    next_button = driver.find_elements(By.CSS_SELECTOR, "button.btn--icon")[::-1]
                    next_arrow = None

                    for btn in next_button:
                        try:
                            use = btn.find_element(By.CSS_SELECTOR, "svg > use")
                            if use.get_attribute("href") == "/dist/icons.svg#circle-arrow":
                                next_arrow = btn
                                break
                        except:
                            continue

                    if not next_arrow:
                        log_and_print("⛔ Next arrow not found.")
                        break

                    # Scroll into view
                    driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", next_arrow)
                    time.sleep(1)

                    # Check if disabled
                    if next_arrow.get_attribute("disabled") is not None:
                        log_and_print("⛔ Next button is disabled. Last page reached.")
                        break

                    # Try clicking
                    try:
                        next_arrow.click()
                    except Exception as e:
                        log_and_print(f"⚠️ Standard click failed: {e}. Trying JS click.")
                        driver.execute_script("arguments[0].click();", next_arrow)

                    # Wait for page to change
                    wait.until(EC.staleness_of(first_card))
                    page += 1
                    time.sleep(2)

                except NoSuchElementException:
                    log_and_print("ℹ️ No pagination button found.")
                    break
                except TimeoutException:
                    log_and_print("⚠️ Page did not change — possibly last page.")
                    break



        # ==========================
        # # Save to CSV
        if all_data:
            os.makedirs("data", exist_ok=True)
            filename = f"data/hso_jobs_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            pd.DataFrame(all_data).to_csv(filename, index=False)
            log_and_print(f"📁 Data saved to {filename}")
        else:
            log_and_print("⚠️ No data scraped.")


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
    scrape_hso_jobs()
