import time
import traceback
import pymysql
import re

from selenium import webdriver

from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

from fake_useragent import UserAgent

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'trenbe/'

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

LOG_FILE = SAVE_PATH+'itemLogSearch.log'

ua = UserAgent()
ua.browsers.remove('chrome')
ua_rd = ua.random

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')


def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={ua_rd}")
    return chrome_options


def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'trenbe_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('trenbe_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])


# Fetch products to crawl
def fetch_used_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 2 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} AND p_is_possible_crawling = 1 LIMIT {limit}")
    return cur.fetchall()

def quitDriver(driver):
    try:
        driver.close()
    except Exception as e1:
        pass
    try:
        driver.quit()
    except Exception as e:
        pass

def __main__():
    try:
        init_log(LOG_FILE)

        chrome_options = init_chrome_options()

        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua_rd})
        driver.execute_cdp_cmd('Network.enable', {})

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        cur.execute('select * from grade where m_id = 2')
        tmp_grades = cur.fetchall()

        grades = {}
        for grade in tmp_grades:
            grades[grade['g_market_grade']] = grade['g_id']
        

        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_used_products(cur, last_crawled_p_id, p_count=0)

        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'trenbe_crawled_p_id'")
            conn.commit()

        for product in products:
            driver.get(product['p_url'])
            print(product['p_url'])
            time.sleep(2)

            source = BeautifulSoup(driver.page_source, 'html.parser')
            print(source)
            price = re.sub(r'[,\s원-]', '', source.select_one('.PriceWithTag__Price-mzv8qx-0').text)
            img_urls = ''

            for img in source.select('.alice-carousel__stage > li img'):
                if 'src' in img.attrs:
                    img_urls += ','+img['src']
            img_urls = img_urls.replace(',', '', 1)
            if price=='':
                price=0
            if source.select_one('.ProductOptions__ButtonGroupWrap-pq9f9q-1 > button').text.find('품절') > -1:
                write_log(LOG_FILE, f'sold out p_id : {product["p_id"]}')
                cur.execute(f'update used_product set p_is_possible_crawling = 0 where p_id = {product["p_id"]}')
                g = grades.get(product['p_option'])
                cur.execute('insert into used_product_sell_history(p_id, g_id, psh_selled_datetime, psh_price, psh_is_quickly) values(%s, %s, %s, %s, 0)', (product['p_id'], g, datetime.now(), product['p_price']))
            else:
                if int(price) != product['p_price']:
                    write_log(LOG_FILE, f'update p_id : {product["p_id"]}')
                    cur.execute('update used_product set p_price = %s, p_last_crawling_datetime = %s, p_img_url = %s where p_id = %s', (price, datetime.now(), img_urls, product['p_id']))
            cur.execute("update config set cfg_value = %s where cfg_key = 'trenbe_crawled_p_id'", (product['p_id']))
            conn.commit()
            

        
    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, err)
    finally:
        quitDriver(driver)
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()