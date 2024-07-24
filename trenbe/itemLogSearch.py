import time
import traceback
import pymysql
import re

from selenium import webdriver

from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

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


def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'trenbe_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        # cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('trenbe_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM product WHERE m_id = 2 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()



def __main__():
    try:
        chrome_options = init_chrome_options()

        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id, p_count=0, limit=1)
        for product in products:
            driver.get(product['p_url'])
            time.sleep(2)

            data = driver.execute_script('return dataLayer')
            print(data)

    except Exception:
        err = traceback.format_exc()
        print(err)

    finally:
        driver.quit()
        conn.close()

if __name__ == "__main__":
    __main__()