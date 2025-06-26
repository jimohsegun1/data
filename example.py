import os
import time
import logging
import csv
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Setup logging
os.makedirs("log", exist_ok=True)
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
file_handler = logging.FileHandler("log/scrap.log", mode="a", encoding="utf-8")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
)
console_handler = logging.StreamHandler()
console_handler.setFormatter(logging.Formatter("%(levelname)s - %(message)s"))
logger.addHandler(file_handler)
logger.addHandler(console_handler)

# Setup output folder
os.makedirs("data", exist_ok=True)
OUTPUT_CSV = "data/job_results.csv"

def setup_driver(headless=True):
    options = uc.ChromeOptions()
    options.headless = headless
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument(
        "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36"
    )
    driver = uc.Chrome(options=options)
    if not headless:
        driver.maximize_window()
    return driver


def load_page(driver, url, wait_timeout=20):
    try:
        driver.get(url)
        logger.info(f"Navigated to {url}")
        WebDriverWait(driver, wait_timeout).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-item"))
        )
        logger.info("Job listings loaded")
        return True
    except Exception as e:
        logger.error(f"Error loading page: {e}")
        return False


def go_to_next_page(driver):
    try:
        nav = driver.find_element(By.CLASS_NAME, "job-manager-pagination")
        next_button = nav.find_element(By.XPATH, './/a[text()="→"]')
        next_button.click()
        logger.info("Clicked forward arrow to go to next page")
        return True
    except NoSuchElementException:
        logger.info("No forward arrow found; last page reached")
        return False
    except Exception as e:
        logger.error(f"Error clicking forward arrow: {e}")
        return False


def extract_details_from_job(driver, job_url):
    try:
        driver.execute_script("window.open(arguments[0]);", job_url)
        driver.switch_to.window(driver.window_handles[-1])
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "job-description"))
        )
        job_desc = driver.find_element(By.CLASS_NAME, "job-description").text.strip()
        driver.close()
        driver.switch_to.window(driver.window_handles[0])
        return job_desc
    except Exception as e:
        logger.warning(f"Could not extract job details from {job_url}: {e}")
        if len(driver.window_handles) > 1:
            driver.close()
            driver.switch_to.window(driver.window_handles[0])
        return "N/A"


def extract_listings_from_page(driver):
    listings = driver.find_elements(By.CLASS_NAME, "job-item")
    job_data = []

    for i in range(len(listings)):
        try:
            # Refetch listings to avoid stale references
            listings = driver.find_elements(By.CLASS_NAME, "job-item")
            listing = listings[i]

            title = listing.find_element(By.TAG_NAME, "h3").text.strip()
            location = listing.find_element(By.CLASS_NAME, "job-location").text.strip()
            date_posted = listing.find_element(By.CLASS_NAME, "job-date").text.strip()

            # Click into the job listing
            listing.click()
            time.sleep(1)  # small wait to allow transition

            # Wait and extract full job description
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-description"))
            )
            job_desc = driver.find_element(
                By.CLASS_NAME, "job-description"
            ).text.strip()

            job_data.append(
                {
                    "title": title,
                    "location": location,
                    "date_posted": date_posted,
                    "description": job_desc,
                }
            )

            logger.info(f"Scraped: {title}")

            # Return to job listing page
            driver.back()
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-item"))
            )
            time.sleep(1)

        except Exception as e:
            logger.error(f"Error scraping job at index {i}: {e}")
            continue

    return job_data


def paginate_through_all_pages(driver, start_url, wait_timeout=20, delay=3):
    if not load_page(driver, start_url, wait_timeout):
        return []

    all_jobs = []
    current_page = 1
    while True:
        logger.info(f"Scraping page {current_page}")
        page_jobs = extract_listings_from_page(driver)
        all_jobs.extend(page_jobs)

        if not go_to_next_page(driver):
            break
        time.sleep(delay)
        try:
            WebDriverWait(driver, wait_timeout).until(
                EC.presence_of_element_located((By.CLASS_NAME, "job-item"))
            )
        except TimeoutException:
            logger.warning("Timeout waiting for jobs to load on new page")
            break
        current_page += 1

    logger.info("Pagination complete")
    return all_jobs


def save_to_csv(jobs, filename=OUTPUT_CSV):
    keys = ["title", "location", "posted", "url", "description"]
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(jobs)
    logger.info(f"Saved {len(jobs)} jobs to {filename}")


if __name__ == "__main__":
    url = "https://conspicuous.com/jobs/"
    driver = setup_driver(headless=True)
    jobs = paginate_through_all_pages(driver, url)
    save_to_csv(jobs)
    driver.quit()
