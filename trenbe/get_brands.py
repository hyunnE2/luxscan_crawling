from bs4 import BeautifulSoup
from selenium.webdriver.common.by import By
from selenium import webdriver
import time

from dotenv import load_dotenv
import os

load_dotenv()

SAVE_PATH = os.environ.get('SAVE_PATH')+'trenbe/'


# Define the base URL
base_url = "https://www.trenbe.com/used/brands?consonant={}&lang=en"

# Create a list to store brand information
brands = []


chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})


driver.get('https://www.trenbe.com/brands')
time.sleep(2)

driver.find_element(By.CSS_SELECTOR, '#all-and-used-filter-btn > div.AllUsedFilterToggle__UsedRoundedBtn-sc-13xobwy-3').click()
time.sleep(2)

def brand_get_type(consonant):
    url = base_url.format(consonant)
    
    # Send a GET request to the URL
    driver.get(url)
    time.sleep(2)
    
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Find the container div
    container = soup.select_one(".SearchBrandList__BrandListWrap-sc-12rxqu4-0")
    
    if container:
        # Loop through each brand div in the container
        for brand_div in container.select("div"):
            # Extract the English and Korean brand names
            eng_name = brand_div.select_one(".SearchBrandCard__BrandCardMainName-sc-1qk47b7-2")
            kor_name = brand_div.select_one(".SearchBrandCard__BrandCardSubName-sc-1qk47b7-3")
            
            if eng_name and kor_name:
                brands.append((eng_name.text.strip(), kor_name.text.strip()))



# Loop through A to Z
for char in range(65, 91):  # ASCII values for A-Z
    consonant = chr(char)
    brand_get_type(consonant)
brand_get_type('Etc.')

# Write the brands to a file
with open(SAVE_PATH+"brand.txt", "w", encoding="utf-8") as file:
    for eng_name, kor_name in brands:
        file.write(f"{eng_name},{kor_name}\n")


driver.quit()