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

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 2')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '').upper()] = brand['b_id']

    return brands

def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 2')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    return grades

def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

try:
    # Create a new instance of the Chrome driver
    chrome_options = init_chrome_options()
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)

    brands = fetch_brand(cur)
    grades = fetch_grade(cur)

    for i in range(1, 101):  # Starting range from 1 to 100
        url = f'https://www.trenbe.com/Owned?sort=latest&brandType=0&options=owned&page={i}'

        driver.get(url)
        time.sleep(2)

        write_log(LOG_FILE, f'get url : {url}')

        last_height = driver.execute_script("return document.body.scrollHeight")
        new_height = 0

        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.4)  # Adjust sleep time as needed
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 500
        time.sleep(4)
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
                
                upper_brand = tmp_product['brand'].replace(' ', '').upper()
                if brands.get(upper_brand) == None:
                    cur.execute(f"insert into brand(`m_id`, `b_name`, `b_search_keyword`) values (5, '{tmp_product['brand']}', '{tmp_product['brand']}')")
                    cur.execute("select * from brand where m_id = 5 order by b_id desc limit 1")
                    b_id = cur.fetchone()['b_id']

                    brands[upper_brand] = b_id
                else:
                    b_id = brands.get(upper_brand)

                tmp_product['brand'] = b_id
                # Insert data into the product table
                sql = """
                INSERT INTO used_product (m_id, b_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
                VALUES (2, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
                ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
                """
                cur.execute(sql, (tmp_product['brand'], grades.get(tmp_product['grade']), tmp_product['name'], tmp_product['price'], 'https://www.trenbe.com'+tmp_product['url']))
                conn.commit()

            except Exception as e:
                write_log(LOG_FILE, f"Error inserting used_product: {e}")

        time.sleep(2)  # Pause before moving to the next page
        write_log(LOG_FILE, f'successed : {url} at {datetime.now()}')

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    driver.quit()
    conn.close()
    write_log(LOG_FILE, f"End at: {datetime.now()}")