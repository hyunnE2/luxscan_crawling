from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.common.exceptions import NoAlertPresentException
from bs4 import BeautifulSoup
import time
import traceback
import pymysql
import re
from datetime import datetime
from dotenv import load_dotenv
import os

from fake_useragent import UserAgent

# .env 파일에서 환경 변수를 로드합니다.
load_dotenv()

# 데이터베이스 구성 설정 (DB 자격 증명은 .env 파일에서 로드됩니다.)
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 로그 파일의 저장 경로를 정의합니다.
SAVE_PATH = os.environ.get('SAVE_PATH') + 'reebonz/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    """
    로그 파일을 초기화하고 시작 시간을 기록합니다.
    """
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    """
    지정된 로그 파일에 메시지를 기록합니다.
    """
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 마지막으로 크롤링된 제품 ID를 가져오는 함수
def get_last_crawled_p_id(cur):
    """
    config 테이블에서 마지막으로 크롤링된 제품 ID를 가져옵니다.
    """
    cur.execute("SELECT * FROM config WHERE cfg_key = 'reebonz_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        # 만약 기록이 없다면 초기 값을 0으로 설정합니다.
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('reebonz_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 중고 제품을 가져오는 함수
def fetch_used_products(cur, last_crawled_p_id, p_count=80, limit=200):
    """
    중고 제품 테이블에서 크롤링이 필요한 제품을 조건에 맞게 가져옵니다.
    """
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 5 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} and p_is_possible_crawling = 1 LIMIT {limit}")
    return cur.fetchall()

# 크롬 옵션을 초기화하는 함수
def init_chrome_options(ua):
    """
    크롬 드라이버의 옵션을 초기화하고, 사용자 에이전트를 설정합니다.
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")  # 브라우저를 숨김 모드로 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,960")
    chrome_options.add_argument(f"user-agent={ua}")
    return chrome_options

# 중고 제품 정보를 업데이트하는 함수
def update_used_product(cur, product, is_selled):
    """
    중고 제품의 상태를 업데이트하고, 판매된 경우 판매 내역에 기록합니다.
    """
    cur.execute('update used_product set p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s',
                (0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into used_product_sell_history(`p_id`, `g_id`, `psh_sold_datetime`, `psh_price`) values(%s, %s, %s, %s)',
                    (product['p_id'], product['g_id'], datetime.now(), product['p_price']))

# 드라이버 종료 함수
def quitDriver(driver):
    """
    웹 드라이버를 종료합니다.
    """
    try:
        driver.close()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass

# 메인 함수
def __main__():
    try:
        # 사용자 에이전트를 초기화합니다.
        ua = UserAgent()
        ua.browsers.remove('chrome')  # Chrome 사용자 에이전트를 목록에서 제거
        ua = ua.random  # 무작위로 사용자 에이전트 생성

        init_log(LOG_FILE)  # 로그 파일 초기화

        # 데이터베이스 연결
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 크롬 드라이버를 초기화
        chrome_options = init_chrome_options(ua)
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
        driver.execute_cdp_cmd('Network.enable', {})

        # 마지막으로 크롤링된 제품 ID를 가져옵니다.
        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_used_products(cur, last_crawled_p_id, p_count=0)

        # 크롤링할 제품이 없을 경우 설정값 초기화
        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'reebonz_crawled_p_id'")
            conn.commit()

        # 각 제품을 크롤링합니다.
        for product in products:
            driver.get(product['p_url'])
            time.sleep(5)  # 페이지 로드 대기

            try:
                # 판매된 제품인 경우, 알림 창을 확인하여 처리합니다.
                alert = driver.switch_to.alert
                alert.accept()
                write_log(LOG_FILE, f"selled found : p_url {product['p_url']}")
                update_used_product(cur, product, True)
                continue  # 다음 제품으로 넘어가기
            except NoAlertPresentException:
                pass

            # 팝업을 닫기 위해 버튼을 클릭
            try:
                driver.find_elements(By.CSS_SELECTOR, '#popupModal .footer button')[0].click()
                time.sleep(1)
            except:
                pass

            try:
                # 페이지에서 제품 정보를 파싱합니다.
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                # 가격 정보를 파싱하고 이미지 URL을 수집합니다.
                product['p_price'] = re.sub(r'[,\s원-]', '', soup.select_one('.main-section .price').text.strip())
                product['p_img_url'] = ','.join([img['src'] for img in soup.select('.product-image-view .swiper-wrapper img')])
                buy_btn = soup.select_one('#buttonsArea > ul')

                # "구매하기" 버튼이 없으면 판매 완료로 처리
                if buy_btn.text.find('구매하기') < 0:
                    write_log(LOG_FILE, f"p_url {product['p_url']}")
                    update_used_product(cur, product, True)
                else:
                    update_used_product(cur, product, False)

            except Exception:
                txt = soup.select_one('#buttonsArea').text if soup.select_one('#buttonsArea') else ''
                rent = soup.select_one('.coupon-info-wrap').text if soup.select_one('.coupon-info-wrap') else ''
                if '날짜 선택하기' in txt or '렌트' in txt or '구독' in txt or '첫 렌트 할인' in rent:
                    cur.execute('update used_product set p_is_possible_crawling = 0 where p_id = %s', product['p_id'])
                else:
                    err = traceback.format_exc()
                    write_log(LOG_FILE, f"Error: {err}")
                    break

            # config 테이블에 마지막 크롤링된 제품 ID 업데이트
            cur.execute("update config set cfg_value = %s where cfg_key = 'reebonz_crawled_p_id'", (product['p_id']))
            conn.commit()

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")

    finally:
        # 연결 종료 및 로그 종료 처리
        conn.close()
        quitDriver(driver)
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
