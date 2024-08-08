from selenium import webdriver
from selenium.webdriver.common.by import By

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

LOG_FILE = SAVE_PATH+'usedProductGetCrawlingBrandList.log'

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
        
        brands = fetch_brand(cur)
        # grades = fetch_grade(cur)

        chrome_options = init_chrome_options()

        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
        time.sleep(2)

        scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
        driver.execute_script('window.scrollTo(0, 600);')
        tmp = -1
        scrollY = 0
        while tmp != scrollY:
            scrollY += 20000
            tmp = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            
            time.sleep(4)

            scrollY += 20000
            scrollY = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)

        time.sleep(2)

        soup = BeautifulSoup(driver.page_source, 'html.parser')
        brand_list = soup.select('.StepItemList__ListContainer-sc-4a1pi5-1 > div')
        
        for brand in brand_list:
            brand_eng =  brand.select_one('span').text
            brand_kr = brand.text.replace(brand_eng, '')
            
            b_id = brands.get(brand_eng.replace(' ', ''))
            if brands.get(brand_eng.replace(' ', '')) == None:
                cur.execute('insert into brand(`m_id`, `b_name`, `b_search_keyword`) values(2, %s, %s)', (brand_eng, brand_kr))
                cur.execute('select * from brand order by b_id desc limit 1')
                b_id = cur.fetchone()['b_id']
            
            cur.execute('insert ignore into crawling_product_list(`m_id`, `b_id`) values(2, %s)', (b_id))
            conn.commit()
            

    except Exception:
        err = traceback.format_exc()
        print(err)

    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()