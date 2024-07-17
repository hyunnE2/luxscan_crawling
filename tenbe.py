from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time

from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
db = os.environ.get('DB_TABLE')
charset = os.environ.get('CHARSET')

chrome_options = Options()
# chrome_options.add_argument("--headless=new")  # Uncomment this if you want to run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

# Create a new instance of the Chrome driver
driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)

for i in range(1, 101):  # Starting range from 1 to 100
    url = f'https://www.trenbe.com/Owned?sort=latest&brandType=0&options=owned&page={i}'
    driver.get(url)
    time.sleep(2)

    last_height = driver.execute_script("return document.body.scrollHeight")
    new_height = 0

    while new_height < last_height:
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(0.2)  # Adjust sleep time as needed
        new_height = driver.execute_script("return window.scrollY + window.innerHeight")+300

    html = driver.page_source

    soup = BeautifulSoup(html, 'html.parser')

    product_list = soup.select('#productContainer > div:nth-child(2) > div.trenbe-list-container > div > div > div > ul > div')
    
    for product in product_list:
        product_url = product.select_one('a')['href']
        product_name = product.select_one('.tb-card_info')
        print(product_url)
        print(product_name)
        break

    break  # Remove this if you want to continue to the next page

driver.quit()