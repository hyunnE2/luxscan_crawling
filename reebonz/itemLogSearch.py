from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from bs4 import BeautifulSoup
import time
import traceback
import pymysql
import re
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

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 5')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']
    return brands

def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    # chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,960")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        brands = fetch_brand(cur)

        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id, p_count=0)

        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'reebonz_crawled_p_id'")
            conn.commit()

        for product in products:
            print(product['p_url'])
            driver.get(product['p_url'])

            time.sleep(5)
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            buy_btn = soup.select_one('#buttonsArea > ul')
            if buy_btn == None:
                write_log(LOG_FILE, f"not inserted p_url {product['p_url']}") 
                print(soup.select_one('#buttonsArea'))
            elif soup.select_one('#buttonsArea > ul').text.find('구매하기') < 0:
                write_log(LOG_FILE, f"p_url {product['p_url']}")    
            
            
            continue
            if brands.get(brand) == None:
                cur.execute("insert into brand(m_id, b_name, b_search_keyword) values(5,%s, %s)", (brand, brand))
                cur.execute("select * from brand where m_id = 5 order by b_id desc")
                b_id = cur.fetchone()['b_id']
            else:
                b_id = brands.get(brand)

            cur.execute("update product set b_id = %s, p_price = %s, p_color = %s, p_last_crawling_datetime = %s where p_id = %s", (b_id, price, color, datetime.now(), product['p_id']))
            cur.execute("update config set cfg_value = %s where cfg_key = 'reebonz_crawled_p_id'", (product['p_id']))
            conn.commit()

    except Exception:
        err = traceback.format_exc()
        print(err)

    finally:
        conn.close()
        driver.quit()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()