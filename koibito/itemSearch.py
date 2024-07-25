from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import pymysql
import traceback
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('KREAM_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'trenbe/'

LOG_FILE = SAVE_PATH+'itemSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')
    print(message)

chrome_options = Options()
chrome_options.add_argument("--headless=new")  # Uncomment this if you want to run in headless mode
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

# Create a new instance of the Chrome driver
driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)

try:
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)
    for i in range(1, 101):  # Starting range from 1 to 100
        url = f'https://www.trenbe.com/Owned?sort=latest&brandType=0&options=owned&page={i}'

        driver.get(url)
        time.sleep(2)

        write_log(LOG_FILE, f'get url : {url}')

        last_height = driver.execute_script("return document.body.scrollHeight")
        new_height = 0

        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.2)  # Adjust sleep time as needed
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 500
            print(new_height, last_height)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        product_list = soup.select('#productContainer > div:nth-child(2) > div.trenbe-list-container > div > div > div > ul > div')
        

        for product in product_list:
            
            try:
                tmp_product = {
                    'url': '',
                    'brand': '',
                    'name': '',
                    'price': '',
                    'grade': ''
                }
                
                tmp_product['grade'] = product.select_one('.ProductCard__ProductCardQualityWrap-sc-16qvrdv-3').text.strip()
                tmp_product['url'] = product.select_one('a')['href'].strip()
                tmp_info = product.select('.tb-card_info > div')
                for idx, info in enumerate(tmp_info):
                    if idx == 0:
                        tmp_product['brand'] = info.text.strip()
                    elif idx == 1:
                        tmp_product['name'] = info.text.strip()
                    elif idx == 2:
                        tmp_product['price'] = re.sub(r'[,\s원-]', '', info.text[info.text.find('%')+1:].strip())
                
                cur.execute(f"select * from brand where b_name = '{tmp_product['brand']}'")
                brand = cur.fetchone()
                if brand == None:
                    cur.execute(f"insert into brand(`b_name`) values ('{tmp_product['brand']}')")
                    cur.execute("select * from brand order by b_id desc limit 1")
                    brand = cur.fetchone()
                else:
                    if brand['b_super_id'] != None:
                        tmp_product['brand'] = brand['b_super_id']

                tmp_product['brand'] = brand['b_id']
                # Insert data into the product table
                sql = """
                INSERT INTO product (m_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_option, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
                VALUES (2, %s, %s, %s, %s, 0, 1, %s, 0, '', '', NOW())
                ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
                """
                cur.execute(sql, (tmp_product['brand'], tmp_product['name'], tmp_product['price'], 'https://www.trenbe.com'+tmp_product['url'], tmp_product['grade']))
                conn.commit()

            except Exception as e:
                write_log(LOG_FILE, f"Error inserting product: {e}")

        time.sleep(2)  # Pause before moving to the next page
        write_log(LOG_FILE, f'successed : {url} at {datetime.now()}')

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    driver.quit()
    conn.close()
    write_log(LOG_FILE, f"End at: {datetime.now()}")