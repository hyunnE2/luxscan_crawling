
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import traceback
import pymysql
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

SAVE_PATH = os.environ.get('SAVE_PATH') + 'bunjang/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'bunjang_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('bunjang_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_bunjang_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 6 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 6')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_market_id']] = brand['b_id']
    return brands

def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    
    return chrome_options
 
def scroll_down(driver):
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
    time.sleep(2)  # 로딩 시간 대기


def scrape_data(url, driver):
    driver.get(url)
    products = []
    last_height = driver.execute_script("return document.body.scrollHeight")

    while True:
        scroll_down(driver)
        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break
        last_height = new_height

    items = driver.find_elements(By.CSS_SELECTOR, "a.sc-cWSHoV.hovUBa")  # 실제 아이템 클래스 이름으로 변경 필요
    for item in items:
        try:
            name = item.find_element(By.CLASS_NAME, "sc-fhzFiK").text  # 상품명 클래스 이름으로 변경 필요

            price = item.find_element(By.CLASS_NAME, "sc-lcIPJg").text  # 가격 클래스 이름으로 변경 필요
            price = re.sub(r'[,\s원-]','',price.strip())
            price = 0 if price == '' else price

            img_url = item.find_element(By.CSS_SELECTOR, "img.sc-kOPcWz.elHqEV").get_attribute("src")  # 이미지 URL

            transaction_count = item.find_element(By.CLASS_NAME, "sc-kdBSHD").text  # 거래 수량 클래스 이름으로 변경 필요
            result = re.sub(r'거래|건', '', transaction_count.strip())
            result = re.sub(r'\s+', '', result)
            
            product_url = item.get_attribute("href")

            products.append({
                "url": product_url, 
                "name": name, 
                "price": price, 
                "img_url": img_url, 
                "transaction_count": result
                })
            
        except Exception:
            err = traceback.format_exc()
            write_log(LOG_FILE, f"Error: {err}")

    return products

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
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        brands = fetch_brand(cur)

        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        # 각 brand_id에 대해 데이터 수집
        for brand_id in brands.keys():
            url = f"https://inspection-auth.bunjang.co.kr/showcase/app-keyword/brands?id={brand_id}&category="
            data = scrape_data(url, driver)

            sql = """
                INSERT INTO used_product (m_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_img_url, p_last_crawling_datetime)
                VALUES (6, %s, %s, %s, %s, 0, %s, 0, %s, NOW())
                ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """

            for item in data:
                cur.execute(sql, (brands[brand_id], item['name'], item['price'], item['url'], item['transaction_count'], item['img_url']))
                conn.commit()


    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")

    finally:
        conn.close()
        quitDriver(driver)
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()