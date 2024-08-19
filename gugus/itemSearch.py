from selenium import webdriver

import time
import traceback

from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('GUGUS_URL')

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'gugus/'

LOG_FILE = SAVE_PATH+'itemSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')


def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 4')
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

def quitDriver(driver):
    try:
        driver.close()
    except Exception as e1:
        pass
    try:
        driver.quit()
    except Exception as e:
        pass

try:
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)

    grades = fetch_grade(cur)

    chrome_options = init_chrome_options()

    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    driver.execute_cdp_cmd('Network.enable', {})

    url = f'{base_url}/shopping/new_update.asp?sm_date=0&PS=96&'
    i = 1
    while True:
        driver.get(url+'GP='+str(i))
        time.sleep(2)

        last_height = driver.execute_script("return document.body.scrollHeight")
        new_height = 0

        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.2)  # Adjust sleep time as needed
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 300

        soup = BeautifulSoup(driver.page_source, 'html.parser')

        products = soup.select('.productListSec > ul > li')
        if len(products) < 1:
            if i == 1:
                write_log(LOG_FILE, f'not found products')
            break
        else:
            write_log(LOG_FILE, f"loaded product count : {len(products)}")
            
        for product in products:
            p_url = product.select_one('.prod > a')['href']
            p_info = product.select('.txt > p')

            name = p_info[0].text
            g_id = grades.get(p_info[1].select_one('.condition > img')['alt'])
            price = p_info[1].select_one('.numType1').text
            price = re.sub(r'[,\s원-]', '', price.strip())

            sql = """
            INSERT INTO used_product (m_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
            VALUES (4, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
            ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """
            cur.execute(sql, (g_id, name, price, base_url+p_url))
            conn.commit()
        i += 1    
        

except Exception:
    e = traceback.format_exc()
    write_log(LOG_FILE, f"Error: {e}")
finally:
    conn.close()
    quitDriver(driver)
    write_log(LOG_FILE, f"End at: {datetime.now()}")