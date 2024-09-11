from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
import time

from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

from fake_useragent import UserAgent

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

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 5')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '').upper()] = brand['b_id']

    return brands
    
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 5')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    return grades

def init_chrome_options(ua):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={ua}")
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
    ua = UserAgent()
    ua.browsers.remove('chrome')
    ua = ua.random
    
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)
    
    brands = fetch_brand(cur)
    grades = fetch_grade(cur)

    chrome_options = init_chrome_options(ua)
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
    driver.execute_cdp_cmd('Network.enable', {})

    url = f'{base_url}/events/28635'
    driver.get(url)
    time.sleep(4)

    last_height = driver.execute_script("return document.body.scrollHeight")
    new_height = 0
    while True:
        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.2)  # Adjust sleep time as needed
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 300

        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button.btn.btn--more")

            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            last_height = driver.execute_script("return document.body.scrollHeight") + 300
        except NoSuchElementException:
            write_log(LOG_FILE, 'not search more button')
            break

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
        if g_id == None:
            cur.execute('insert into `grade`(`m_id`, `g_market_grade`) values(5, %s)', (grade))
            cur.execute('select * from `grade` where `g_market_grade` = %s', (grade))
            g_id = cur.fetchone()['g_id']
            grades[grade] = g_id

        name = product.select_one('.product-name').text
        price = re.sub(r'[,\s원-]', '', product.select_one('.price').text.strip())

        upper_brand = brand.replace(' ', '').upper()
        if brands.get(upper_brand) == None:
            cur.execute(f"insert into brand(`m_id`, `b_name`, `b_search_keyword`) values (5, '{brand}', '{brand}')")
            cur.execute("select * from brand where m_id = 5 order by b_id desc limit 1")
            b_id = cur.fetchone()['b_id']

            brands[upper_brand] = b_id
        else:
            b_id = brands.get(upper_brand)
        
        sql = """
        INSERT INTO used_product (m_id, g_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
        VALUES (5, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
        ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
        """
        cur.execute(sql, (g_id, b_id, name, price, base_url+p_url))
        conn.commit()

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    conn.close()
    quitDriver(driver)
    write_log(LOG_FILE, f"End at: {datetime.now()}")