import time
import traceback
import pymysql
import re

from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os
from fake_useragent import UserAgent

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 설정 정보
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 경로 및 설정 값
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# UserAgent 생성 및 설정
ua = UserAgent()
ua.browsers.remove('chrome')
ua_rd = ua.random

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 크롬 옵션 초기화 함수
def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={ua_rd}")
    return chrome_options

# 마지막으로 크롤링한 상품 ID 가져오기
def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'trenbe_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('trenbe_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 상품 가져오기
def fetch_used_products(cur, last_crawled_p_id, p_count=80, limit=200):
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 2 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} AND p_is_possible_crawling = 1 LIMIT {limit}")
    return cur.fetchall()

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

# 메인 함수
def __main__():
    try:
        # 로그 파일 초기화
        init_log(LOG_FILE)

        # 크롬 드라이버 옵션 초기화 및 드라이버 생성
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua_rd})
        driver.execute_cdp_cmd('Network.enable', {})

        # 데이터베이스 연결
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 등급 정보 가져오기
        cur.execute('select * from grade where m_id = 2')
        tmp_grades = cur.fetchall()
        grades = {}
        for grade in tmp_grades:
            grades[grade['g_market_grade']] = grade['g_id']

        # 마지막으로 크롤링한 상품 ID 가져오기
        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_used_products(cur, last_crawled_p_id, p_count=0)

        # 크롤링할 상품이 없는 경우 처리
        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'trenbe_crawled_p_id'")
            conn.commit()

        # 각 상품에 대해 크롤링 진행
        for product in products:
            driver.get(product['p_url'])
            time.sleep(4)  # 페이지 로드 시간 대기

            # 페이지 소스 파싱
            source = BeautifulSoup(driver.page_source, 'html.parser')
            price = re.sub(r'[,\s원-]', '', source.select_one('.PriceWithTag__Price-mzv8qx-0').text)
            img_urls = ''

            # 이미지 URL 추출
            for img in source.select('.alice-carousel__stage > li img'):
                if 'src' in img.attrs:
                    img_urls += ',' + img['src']
            img_urls = img_urls.replace(',', '', 1)

            # 가격이 없을 경우 기본값 설정
            if price == '':
                price = 0

            # 품절 여부 확인 및 처리
            if source.select_one('.ProductOptions__ButtonGroupWrap-pq9f9q-1 > button').text.find('품절') > -1:
                write_log(LOG_FILE, f'sold out p_id : {product["p_id"]}')
                cur.execute(f'update used_product set p_is_possible_crawling = 0 where p_id = {product["p_id"]}')
                g = grades.get(product['p_option'])
                cur.execute('insert into used_product_sell_history(p_id, g_id, psh_sold_datetime, psh_price, psh_is_quickly) values(%s, %s, %s, %s, 0)', (product['p_id'], g, datetime.now(), product['p_price']))
            else:
                write_log(LOG_FILE, f'update p_id : {product["p_id"]}')
                cur.execute('update used_product set p_price = %s, p_last_crawling_datetime = %s, p_img_url = %s where p_id = %s', (price, datetime.now(), img_urls, product['p_id']))

            # 마지막으로 크롤링한 상품 ID 업데이트
            cur.execute("update config set cfg_value = %s where cfg_key = 'trenbe_crawled_p_id'", (product['p_id']))
            conn.commit()

    except Exception:
        # 예외 발생 시 로그에 기록
        err = traceback.format_exc()
        write_log(LOG_FILE, err)
    finally:
        # 드라이버 종료 및 데이터베이스 연결 종료
        quitDriver(driver)
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 호출
if __name__ == "__main__":
    __main__()
