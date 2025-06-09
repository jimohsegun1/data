import logging
import pandas as pd
import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from tqdm import tqdm
import os

# --- Set up logging ---
logging.basicConfig(
    filename='nigelfrank_scraper.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(levelname)s - %(message)s')
console.setFormatter(formatter)
logging.getLogger('').addHandler(console)

# --- Scraper function ---
def nigelfrank_scraper(url, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--ignore-certificate-errors')
            options.add_argument('--ignore-ssl-errors')
            options.add_argument("--headless=new")
            options.add_argument("--disable-blink-features=AutomationControlled")

            driver = webdriver.Chrome(options=options)
            driver.get(url)

            WebDriverWait(driver, 15).until(
                EC.visibility_of_element_located((By.XPATH, '//*[@id="__next"]/div/div[1]/div[2]/div/div[2]'))
            )

            soup = BeautifulSoup(driver.page_source, 'lxml')
            driver.quit()

            job_list = soup.find_all('div', class_="sc-AykKG sc-fzXfQW BqA-ds")
            logging.info(f"[{url}] Jobs found: {len(job_list)}")

            job_data = []
            for job in job_list:
                link_em = job.find('a', class_="sc-AykKE fwNdOp")
                job_url = "https://www.nigelfrank.com" + link_em['href'] if link_em and link_em.get('href') else None
                job_id = job_url.split("/")[-2] if job_url else None

                title = job.find('h3', class_="sc-AykKD fECRJb jobTitle")
                location = job.find('p', class_="location")

                info_list_em = job.find('ul', class_="particulars")
                salary = role_type = level = None
                if info_list_em:
                    info_em = info_list_em.find_all('li')
                    if len(info_em) > 0: salary = info_em[0].get_text(strip=True)
                    if len(info_em) > 1: role_type = info_em[1].get_text(strip=True)
                    if len(info_em) > 2: level = info_em[2].get_text(strip=True).split(":")[-1].strip()

                job_desc_em = job.find("div", class_="jobDescription")
                description = job_desc_em.get_text(strip=True) if job_desc_em else ""

                data = {
                    "title": title.get_text(strip=True) if title else None,
                    "job_id": job_id,
                    "job_url": job_url,
                    "location": location.get_text(strip=True) if location else None,
                    "salary": salary,
                    "role_type": role_type,
                    "level": level,
                    "description": description
                }

                job_data.append(data)
            return job_data

        except (TimeoutException, WebDriverException) as e:
            retries += 1
            logging.warning(f"Retry {retries}/{max_retries} for {url} due to error: {e}")
            time.sleep(2)  # Wait a bit before retrying
            try:
                driver.quit()
            except:
                pass
        except Exception as e:
            logging.error(f"Failed scraping {url}: {e}")
            try:
                driver.quit()
            except:
                pass
            return []

    logging.error(f"Max retries exceeded for {url}")
    return []

# --- Paginated URLs ---
start_urls = [
    f"https://www.nigelfrank.com/microsoft-jobs?newJobs=&keyword=&location=&jobType=both&page={i}&remote=&security=&salaryFrom=&salaryTo=&salaryCurrency=&segment=&product="
    for i in range(1, 148)
]

# --- CSV Setup ---
csv_file = "nigelfrank.csv"
file_exists = os.path.exists(csv_file)

# Write header only once
if not file_exists:
    pd.DataFrame(columns=[
        "title", "job_id", "job_url", "location", "salary", "role_type", "level", "description"
    ]).to_csv(csv_file, index=False)

# --- Main Loop with tqdm ---
total_scraped = 0
for url in tqdm(start_urls, desc="Scraping NigelFrank pages"):
    result = nigelfrank_scraper(url)
    if result:
        df = pd.DataFrame(result)
        df.to_csv(csv_file, mode='a', header=False, index=False)
        total_scraped += len(result)
    time.sleep(1)

logging.info(f"✅ Done scraping. Total jobs scraped: {total_scraped}")
print(f"\n✅ Finished! Total jobs scraped: {total_scraped}. Saved to {csv_file}")
