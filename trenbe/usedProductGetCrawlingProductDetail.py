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

import re

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

LOG_FILE = SAVE_PATH+'usedProductGetCrawlingProductDetail.log'

def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def fetch_crawling_products(cur, last_crawled_pr_id):
    cur.execute('select * from product_resale join brand on product_resale.b_id = brand.b_id where brand.m_id = 2 and pr_id > %s order by pr_id limit 100', (last_crawled_pr_id))
    return cur.fetchall()

def url_parser(url, params_name):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)

    # brandId 추출
    return query_params.get(params_name, [None])[0]

def get_last_crawled_pr_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'trenbe_crawled_pr_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('trenbe_crawled_pr_id', 0)")
        return 0
    return int(result['cfg_value'])

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

        last_crawled_pr_id = get_last_crawled_pr_id(cur)
        crawling_product = fetch_crawling_products(cur, last_crawled_pr_id)

        chrome_options = init_chrome_options()

        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        if len(crawling_product) < 1:
            cur.execute('delete from config where cfg_key="trenbe_crawled_pr_id"')
            conn.commit()
        
        brand_keyword = ''
        for idx, product in enumerate(crawling_product):
            product_found = False

            if brand_keyword != product['b_search_keyword']:
                driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
                time.sleep(2)

                driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(product['b_search_keyword'])
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1').click()
                time.sleep(3)
                brand_keyword = product['b_search_keyword']

                driver.execute_script('window.scrollTo(0, 180);')
            driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(product['pr_name'])
            
            if idx == 0:
                time.sleep(10)
                driver.find_elements(By.CSS_SELECTOR, '.ab-iam-root button')[0].click()

            time.sleep(2)
            driver_product_list = driver.find_elements(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1 > div')
            for driver_product in driver_product_list:
                if driver_product.text.find(product['pr_name']) > -1:
                    product_found = True

                    scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
                    driver.execute_script(f'arguments[0].scrollTo(0, {driver_product.location["y"]});', scrollItem)
                    time.sleep(2)

                    driver_product.click()
                    time.sleep(2)

                    driver_product_detail = driver.find_elements(By.CSS_SELECTOR,'.ConfirmModal__DataLineContainer-sc-1brpfr9-5 dd')

                    category = driver_product_detail[0].text
                    brand = driver_product_detail[1].text
                    pr_detail_name = driver_product_detail[2].text

                    # if(pr_detail_name == product['pr_name'], brand == product['b_search_keyword']):pass

                    driver.find_element(By.CSS_SELECTOR, '.ConfirmModal__ConfirmModalWrap-sc-1brpfr9-0 button.confirm').click()
                    time.sleep(1)

                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    tds = soup.select('.SiseContents__PriceTable-sc-1vnoo68-5 td')


                    avg_sale = re.sub(r'[,\s원-]', '',tds[1].text.strip())
                    avg_buy = re.sub(r'[,\s원-]', '',tds[2].text.strip())
                    max_sale = re.sub(r'[,\s원-]', '',tds[4].text.strip())
                    max_buy = re.sub(r'[,\s원-]', '',tds[5].text.strip())
                    
                    print(product['pr_id'])

                    cur.execute('update product_resale set pr_category=%s, pr_update_datetime=%s, pr_avg_sale=%s, pr_avg_buy=%s, pr_max_sale=%s, pr_max_buy=%s where pr_id = %s', (category, datetime.now(), avg_sale,avg_buy,max_sale,max_buy, product['pr_id']))
                    cur.execute('update config set cfg_value = %s where cfg_key = "trenbe_crawled_pr_id"', (product['pr_id']))
                    conn.commit()

                    driver.back()
                    time.sleep(1)
                    break
            if not product_found:
                driver.refresh()
                time.sleep(2)
            

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, err)

    finally:
        driver.quit()
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()