from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import pymysql
import traceback
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 기본 URL 및 데이터베이스 설정 정보
base_url = os.environ.get('KREAM_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 저장 경로 및 로그 파일 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'
LOG_FILE = SAVE_PATH + 'itemSearch.log'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 브랜드 정보를 데이터베이스에서 가져오는 함수
def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 2')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_search_keyword'].replace(' ', '').upper()] = brand['b_id']
    return brands

# 등급 정보를 데이터베이스에서 가져오는 함수
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 2')
    tmp_grades = cur.fetchall()
    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']
    return grades

# 크롬 옵션 초기화 함수
def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

# 드라이버 종료 함수
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
    # 크롬 드라이버 및 데이터베이스 연결 설정
    chrome_options = init_chrome_options()
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)

    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)

    # 데이터베이스에서 브랜드 및 등급 정보 가져오기
    brands = fetch_brand(cur)
    grades = fetch_grade(cur)

    # 1페이지부터 100페이지까지 크롤링
    for i in range(1, 101):
        url = f'https://www.trenbe.com/Owned?sort=latest&brandType=0&options=owned&page={i}'

        driver.get(url)
        time.sleep(2)

        write_log(LOG_FILE, f'get url : {url}')

        # 페이지 전체를 스크롤하여 모든 상품을 로드
        last_height = driver.execute_script("return document.body.scrollHeight")
        new_height = 0

        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.4)  # 스크롤 속도 조정
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 500
        time.sleep(4)

        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        product_list = soup.select('#productContainer > div:nth-child(2) > div.trenbe-list-container > div > div > div > ul > div')

        # 각 상품에 대한 정보 추출 및 데이터베이스 삽입
        for product in product_list:
            try:
                tmp_product = {
                    'url': '',
                    'brand': '',
                    'name': '',
                    'price': '',
                    'grade': ''
                }

                # 상품 정보 파싱
                tmp_product['grade'] = product.select_one('.ProductCard__ProductCardQualityWrap-sc-16qvrdv-3').text.strip()
                tmp_product['url'] = product.select_one('a')['href'].strip()
                tmp_info = product.select('.tb-card_info > div')
                for idx, info in enumerate(tmp_info):
                    if idx == 0:
                        tmp_product['brand'] = info.text.strip()
                    elif idx == 1:
                        tmp_product['name'] = info.text.strip()
                    elif idx == 2:
                        tmp_product['price'] = re.sub(r'[,\s원-]', '', info.text[info.text.find('%') + 1:].strip())

                # 브랜드 정보 확인 및 삽입
                upper_brand = tmp_product['brand'].replace(' ', '').upper()
                if brands.get(upper_brand) is None:
                    cur.execute("insert into brand(`m_id`, `b_name`, `b_search_keyword`) values (2, %s, %s)", (tmp_product['brand'], tmp_product['brand']))
                    cur.execute("select * from brand where m_id = 2 order by b_id desc limit 1")
                    b_id = cur.fetchone()['b_id']
                    brands[upper_brand] = b_id
                else:
                    b_id = brands.get(upper_brand)

                tmp_product['brand'] = b_id

                # 데이터베이스에 상품 정보 삽입
                sql = """
                INSERT INTO used_product (m_id, b_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
                VALUES (2, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
                ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
                """
                cur.execute(sql, (tmp_product['brand'], grades.get(tmp_product['grade']), tmp_product['name'], tmp_product['price'], 'https://www.trenbe.com' + tmp_product['url']))
                conn.commit()

            except Exception:
                e = traceback.format_exc()
                write_log(LOG_FILE, f"Error inserting used_product: {e}")

        time.sleep(2)  # 다음 페이지로 넘어가기 전에 대기
        write_log(LOG_FILE, f'successed : {url} at {datetime.now()}')

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    quitDriver(driver)
    conn.close()
    write_log(LOG_FILE, f"End at: {datetime.now()}")
