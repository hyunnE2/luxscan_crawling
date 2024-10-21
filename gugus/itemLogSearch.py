from selenium import webdriver
from selenium.common.exceptions import NoAlertPresentException
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import traceback
import pymysql
import re
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# DB 설정 정보 로드
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 로그 파일 경로 및 크롬 드라이버 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'gugus/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# 로그 파일 초기화
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 마지막으로 크롤링한 p_id 가져오기
def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'gugus_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('gugus_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 제품 목록 가져오기
def fetch_used_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 4 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} AND p_is_possible_crawling=1 LIMIT {limit}")
    return cur.fetchall()

# 브랜드 목록 가져오기
def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 4')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name']] = brand['b_id']
    return brands

# 크롬 옵션 초기화
def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")
    return chrome_options

# 로그 삽입 함수
def insert_log(cur, product, conn):
    cur.execute("update used_product set b_id = %s, p_is_possible_crawling = %s, p_price = %s, p_last_crawling_datetime = %s where p_id = %s", (product['b_id'], 0, product['p_price'], datetime.now(), product['p_id']))
    cur.execute("insert into used_product_sell_history(p_id, psh_sold_datetime, psh_price) values(%s, %s, %s)", (product['p_id'], datetime.now(), product['p_price']))
    cur.execute("update config set cfg_value = %s where cfg_key = 'gugus_crawled_p_id'", (product['p_id']))
    conn.commit()

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

# 메인 함수 정의
def __main__():
    driver = None
    conn = None

    try:
        # 로그 초기화 및 DB 연결 설정
        init_log(LOG_FILE)
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 크롬 드라이버 및 네트워크 설정
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        # 구구스 홈페이지 접속
        driver.get('https://www.gugus.co.kr')
        time.sleep(2)

        # 팝업 닫기 시도
        try:
            driver.find_element(By.CSS_SELECTOR, '#bodyDialog4.open')
            driver.find_element(By.CSS_SELECTOR, '#bodyDialog4.open .dialog-footer .left-area > button').click()
        except Exception:
            pass

        # 마지막으로 크롤링한 p_id 확인 및 제품 목록 가져오기
        last_crawled_p_id = get_last_crawled_p_id(cur)
        used_products = fetch_used_products(cur, last_crawled_p_id, p_count=0)

        if len(used_products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'gugus_crawled_p_id'")
            conn.commit()

        # 각 제품에 대한 크롤링 작업 시작
        for product in used_products:
            driver.get(product['p_url'])
            time.sleep(2)

            # URL이 홈페이지로 리디렉션 되었는지 확인 (판매 완료된 경우)
            if driver.current_url == 'https://www.gugus.co.kr':
                insert_log(cur, product, conn)
                continue

            # 판매 완료 팝업 확인
            try:
                driver.find_element(By.CSS_SELECTOR, ".open #popDialogAlert")
                insert_log(cur, product, conn)
                continue
            except:
                print(traceback.format_exc())
                pass

            # 제품 상세 정보 스크래핑
            soup = BeautifulSoup(driver.page_source, 'html.parser')
            info = soup.select('.prod-detail-info-wrap .scont-box')[0]

            # 이미지 URL 수집
            img_urls = ','.join([i['src'] for i in soup.select('.prod-detail-header .prod-detail-swiper-wrap img')])

            # 가격 및 내용 수집
            price = info.select_one('.prod-price .val').text.strip()
            price = re.sub(r'[,\s원-]', '', price)
            product['p_price'] = price

            content = soup.select_one('#gdsDtlDsct').text.strip()
            product['content'] = content

            # 판매 완료된 경우 로그 삽입
            if price.find('판매완료상품') > -1:
                insert_log(cur, product, conn)
            else:
                # DB 업데이트
                cur.execute("update used_product set p_price = %s, p_img_url = %s, p_content = %s, p_last_crawling_datetime = %s where p_id = %s",(price, img_urls, product['content'], datetime.now(), product['p_id']))
                cur.execute("update config set cfg_value = %s where cfg_key = 'gugus_crawled_p_id'", (product['p_id']))
                conn.commit()

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")

    finally:
        conn.close()
        quitDriver(driver)
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
