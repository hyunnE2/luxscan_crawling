from selenium import webdriver

import time

from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('REEBONZ_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'reebonz/'

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
    print(message)

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 5')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']

    return brands
    
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 5')
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
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)
    
    brands = fetch_brand(cur)
    grades = fetch_grade(cur)

    chrome_options = init_chrome_options()
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    driver.execute_cdp_cmd('Network.enable', {})

    url = f'{base_url}/events/28635'
    driver.get(url)
    time.sleep(2)

    last_height = driver.execute_script("return document.body.scrollHeight")
    new_height = 0

    while new_height < last_height:
        driver.execute_script("window.scrollBy(0, 400);")
        time.sleep(0.2)  # Adjust sleep time as needed
        new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 300
        print(new_height, last_height)

    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.select('.products-list__grid2 > div')

    if len(products) < 1:
        write_log(LOG_FILE, f'not found products')
    else:
        write_log(LOG_FILE, f"loaded product count : {len(products)}")
        
    for product in products:
        
        p_url = product.select_one('a')['href']
        brand = product.select_one('.first-desc').text
        grade = product.select_one('.img-box').text
        g_id = grades.get(grade)
        name = product.select_one('.product-name').text
        price = re.sub(r'[,\s원-]', '', product.select_one('.price').text.strip())

        if brands.get(brand) == None:
            cur.execute(f"insert into brand(`m_id`, `b_name`, `b_search_keyword`) values (5, '{brand}', '{brand}')")
            cur.execute("select * from brand where m_id = 5 order by b_id desc limit 1")
            b_id = cur.fetchone()['b_id']
        else:
            b_id = brands.get(brand)

        sql = """
        INSERT INTO product (m_id, g_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
        VALUES (5, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
        ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
        """
        cur.execute(sql, (g_id, b_id, name, price, base_url+p_url))
        conn.commit()

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    conn.close()
    driver.quit()
    write_log(LOG_FILE, f"End at: {datetime.now()}")