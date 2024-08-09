from selenium import webdriver
from selenium.webdriver.common.by import By

from urllib.parse import urlparse, parse_qs

import time
import traceback
import pymysql

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

LOG_FILE = SAVE_PATH+'usedProductGetCrawlingProductList.log'

def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 2')
    tmp_brands = cur.fetchall()
    
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']
    return brands

def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 2')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']
    
    return grades


def fetch_crawling_brand(cur):
    cur.execute('select * from crawling_product_list join brand on crawling_product_list.b_id = brand.b_id where brand.m_id = 2')
    return cur.fetchall()

def url_parser(url, params_name):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # brandId 추출
    return query_params.get(params_name, [None])[0]

def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1200,960")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options


def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        crawling_brand = fetch_crawling_brand(cur)
        # grades = fetch_grade(cur)

        chrome_options = init_chrome_options()

        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        for b_search_keyword in crawling_brand:
            driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
            time.sleep(2)

            driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(b_search_keyword['b_search_keyword'])
            time.sleep(3)
            driver.find_element(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1').click()

            time.sleep(4)

            b_market_id = url_parser(driver.current_url, 'brandId')
            print(driver.current_url)
            cur.execute('update brand set b_market_id = %s where b_id = %s', (b_market_id, b_search_keyword['b_id']))
            conn.commit()

            scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
            driver.execute_script('window.scrollTo(0, 600);')
            tmp = -1
            scrollY = 0
            print(driver.page_source)
            print('scroll Start')
            while tmp != scrollY:
                scrollY += 20000
                tmp = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
                
                time.sleep(4)

                scrollY += 20000
                scrollY = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            print('scroll end')
            time.sleep(2)

            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_list = soup.select('.StepItemList__ListContainer-sc-4a1pi5-1 > div')
            
            for product in product_list:
                d_product = product.select_one('.ListModelItem__ContentBox-sc-1jm7w42-3')
                if d_product.select_one('.market-measurement-badge') == None: continue
                p_name = product.select_one('p').text

                cur.execute('insert ignore into product_resale(`b_id`, `m_id`, `pr_name`) values(%s, 2, %s)', (b_search_keyword['b_id'], p_name))
                conn.commit()
            conn.commit()

    except Exception:
        err = traceback.format_exc()
        print(err)

    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()