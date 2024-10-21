from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time
import traceback
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 환경 변수에서 URL 및 데이터베이스 설정 정보 가져오기
base_url = os.environ.get('GUGUS_URL')
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

# DB 연결 설정 정보
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 로그 파일 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'gugus/'
LOG_FILE = SAVE_PATH + 'itemSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 등급 데이터 가져오기
def fetch_grade(cur):
    cur.execute('SELECT * FROM grade WHERE m_id = 4')
    tmp_grades = cur.fetchall()
    grades = {grade['g_market_grade']: grade['g_id'] for grade in tmp_grades}
    return grades

# 브랜드 데이터 가져오기
def fetch_brand(cur):
    cur.execute('SELECT * FROM brand WHERE m_id = 4')
    tmp_brands = cur.fetchall()
    brands = {brand['b_name']: brand['b_id'] for brand in tmp_brands}
    return brands

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

# 크롬 드라이버 종료 함수
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
    # DB 연결 및 커서 생성
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)

    # 브랜드 및 등급 데이터 가져오기
    grades = fetch_grade(cur)
    brands = fetch_brand(cur)

    # 크롬 옵션 설정 및 드라이버 초기화
    chrome_options = init_chrome_options()
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
    driver.execute_cdp_cmd('Network.enable', {})

    # URL 설정 및 각 날짜 탭별로 크롤링
    url = f'{base_url}/update?tabDate='
    for i in range(0, 7):
        swp = 'TODAY' if i == 0 else f'{i}DAYAGO'
        driver.get(url + swp)
        time.sleep(2)

        # 페이지 끝까지 스크롤
        last_height = driver.execute_script("return document.body.scrollHeight")
        new_height = 0
        while True:
            driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
            time.sleep(1)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height

        # 페이지 소스 분석
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        products = soup.select('#goods-ul > .grid-item')

        # 각 제품 정보 처리
        for product in products:
            # 제품 URL 추출 및 구성
            p_url = product.select_one('.btn-link')['onclick']
            p_url = base_url + "/goods/viewGoods?goodsNo=" + p_url[p_url.find('(') + 1:p_url.find(')')]

            # 제품 상세 정보 추출
            p_info = product.select_one('.info-box')
            name = p_info.select_one('.title').text.strip()
            brand = p_info.select_one('.brand').text.strip()

            # 브랜드가 존재하지 않으면 추가
            if brands.get(brand) is None:
                cur.execute("INSERT INTO brand(m_id, b_name, b_search_keyword) VALUES (4, %s, %s)", (brand, brand))
                cur.execute("SELECT * FROM brand WHERE m_id = 4 ORDER BY b_id DESC")
                b_id = cur.fetchone()['b_id']
                brands[brand] = b_id
            else:
                b_id = brands.get(brand)

            # 제품 등급 추출 및 추가
            grade = p_info.select_one('.prod-price > span > .text').text.strip()
            g_id = grades.get(grade)
            if g_id is None:
                cur.execute('INSERT INTO `grade`(`m_id`, `g_market_grade`) VALUES (4, %s)', (grade))
                cur.execute('SELECT * FROM `grade` WHERE `g_market_grade` = %s', (grade))
                g_id = cur.fetchone()['g_id']
                grades[grade] = g_id

            # 가격 정보 처리
            price = p_info.select_one('.prod-price > .goods-group').text.strip()
            price = re.sub(r'[,\s원-]', '', price)

            # 데이터베이스에 제품 정보 삽입 또는 업데이트
            sql = """
            INSERT INTO used_product (m_id, b_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
            VALUES (4, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
            ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """
            cur.execute(sql, (b_id, g_id, name, price, p_url))
            conn.commit()

except Exception:
    e = traceback.format_exc()
    write_log(LOG_FILE, f"Error: {e}")

finally:
    # DB 연결 종료 및 드라이버 종료
    conn.close()
    quitDriver(driver)
    write_log(LOG_FILE, f"End at: {datetime.now()}")
