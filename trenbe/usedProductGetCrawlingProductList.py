from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoSuchElementException
from urllib.parse import urlparse, parse_qs
import time
import traceback
import pymysql
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os
import re

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 정보 설정
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 저장 경로 및 실행 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

# 로그 파일 설정
LOG_FILE = SAVE_PATH + 'usedProductGetCrawlingProductList.log'

# 로그 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 기록 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 브랜드 정보 가져오는 함수
def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 2')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']
    return brands

# 등급 정보 가져오는 함수
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 2')
    tmp_grades = cur.fetchall()
    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']
    return grades

# 크롤링할 브랜드 정보 가져오는 함수
def fetch_crawling_brand(cur):
    cur.execute('select * from crawling_product_list join brand on crawling_product_list.b_id = brand.b_id where brand.m_id = 2 ORDER BY cpl_id')
    return cur.fetchall()

# URL에서 특정 매개변수를 파싱하는 함수
def url_parser(url, params_name):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get(params_name, [None])[0]

# 크롬 옵션 설정 함수
def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1200,960")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

# 메인 함수
def __main__():
    try:
        # 로그 파일 초기화
        init_log(LOG_FILE)

        # 데이터베이스 연결
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 크롤링할 브랜드 정보 가져오기
        crawling_brand = fetch_crawling_brand(cur)

        # 크롬 옵션 및 드라이버 설정
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        for b_search_keyword in crawling_brand:
            # 브랜드 검색 페이지로 이동
            driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
            time.sleep(2)

            # 브랜드 검색 입력
            driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(b_search_keyword['b_search_keyword'])
            time.sleep(3)
            driver.find_element(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1').click()
            time.sleep(4)

            # 브랜드 ID 추출
            b_market_id = url_parser(driver.current_url, 'brandId')
            cur.execute('update brand set b_market_id = %s where b_id = %s', (b_market_id, b_search_keyword['b_id']))
            conn.commit()

            try:
                # 스크롤할 요소 찾기
                scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
                driver.execute_script('window.scrollTo(0, 600);')
            except NoSuchElementException:
                write_log(LOG_FILE, 'not search more button')
                continue

            # 페이지 끝까지 스크롤
            tmp = -1
            scrollY = 0
            while tmp != scrollY:
                scrollY += 20000
                tmp = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
                time.sleep(4)

                scrollY += 20000
                scrollY = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            time.sleep(8)

            # HTML 파싱
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            product_list = soup.select('.StepItemList__ListContainer-sc-4a1pi5-1 > div')

            # 상품 정보 처리
            for product in product_list:
                d_product = product.select_one('.ListModelItem__ContentBox-sc-1jm7w42-3')
                if d_product is None:
                    write_log(LOG_FILE, 'product None')
                    continue

                if d_product.select_one('.market-measurement-badge') is None:
                    continue

                p_name = product.select_one('p').text
                try:
                    p_img_url = product.select_one('source')['srcset']
                    p_img_url = p_img_url[:p_img_url.find('1x,')]
                except Exception:
                    p_img_url = ""

                # DB에 상품 정보 삽입
                cur.execute('insert ignore into product_resale(`b_id`, `m_id`, `pr_name`, `pr_img_url`) values(%s, 2, %s, %s)', (b_search_keyword['b_id'], p_name, p_img_url))
                cur.execute('delete from crawling_product_list where cpl_id = %s', (b_search_keyword['cpl_id']))
                conn.commit()

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, err)
    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
