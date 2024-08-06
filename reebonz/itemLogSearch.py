from selenium import webdriver
from selenium.common.exceptions import UnexpectedAlertPresentException
from bs4 import BeautifulSoup
import time
import traceback
import pymysql
import re
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

SAVE_PATH = os.environ.get('SAVE_PATH') + 'reebonz/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'reebonz_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('reebonz_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM product WHERE m_id = 5 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

def init_chrome_options(ua):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,960")
    chrome_options.add_argument(f"user-agent={ua}")
    return chrome_options

def product_update(cur, product, is_selled):
    cur.execute('update product set p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s', (0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into product_sell_history(`p_id`, `g_id`, `psh_datetime`, `psh_price`) values(%s, %s, %s, %s)', (product['p_id'], product['g_id'], datetime.now(), product['p_price']))

def __main__():
    try:
        ua = UserAgent()
        ua.browsers.remove('chrome')
        ua = ua.random

        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
        driver.execute_cdp_cmd('Network.enable', {})


        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id, p_count=0)

        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'reebonz_crawled_p_id'")
            conn.commit()

        for product in products:
            driver.get(product['p_url'])
            time.sleep(5)
            try:
                soup = BeautifulSoup(driver.page_source, 'html.parser')    
                product['p_price'] = re.sub(r'[,\s원-]', '', soup.select_one('.sentry-unmask > .price').text.strip())
                product['p_img_url'] = ','.join([img['src'] for img in soup.select('.product-image-view .swiper-wrapper img')])
                buy_btn = soup.select_one('#buttonsArea > ul')

                if buy_btn.text.find('구매하기') < 0:
                    write_log(LOG_FILE, f"p_url {product['p_url']}")
                    product_update(cur, product, True)
                else:
                    product_update(cur, product, False)

            except UnexpectedAlertPresentException:
                write_log(LOG_FILE, f"selled found : p_url {product['p_url']}")
                product_update(cur, product, True)

            cur.execute("update config set cfg_value = %s where cfg_key = 'reebonz_crawled_p_id'", (product['p_id']))
            conn.commit()

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")

    finally:
        conn.close()
        driver.quit()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()