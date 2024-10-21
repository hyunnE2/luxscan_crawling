from selenium import webdriver
from selenium.webdriver.common.by import By
from urllib.parse import urlparse, parse_qs
import time
import traceback
import pymysql
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os
import re
from fake_useragent import UserAgent

# 환경 변수 로드
load_dotenv()

# 데이터베이스 연결 정보
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 파일 경로 설정 및 로그인 정보
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
crawling_id = os.environ.get('CRAWLING_ID')
crawling_pw = os.environ.get('CRAWLING_PW')

LOG_FILE = SAVE_PATH + 'usedProductGetCrawlingProductDetail.log'

# 로그 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 기록 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 크롤링할 상품 가져오는 함수
def fetch_crawling_products(cur, last_crawled_pr_id):
    cur.execute('select * from product_resale join brand on product_resale.b_id = brand.b_id where brand.m_id = 2 and pr_id > %s order by pr_id limit 200', (last_crawled_pr_id))
    return cur.fetchall()

# URL에서 특정 매개변수를 파싱하는 함수
def url_parser(url, params_name):
    parsed_url = urlparse(url)
    query_params = parse_qs(parsed_url.query)
    return query_params.get(params_name, [None])[0]

# 마지막으로 크롤링된 상품 ID 가져오는 함수
def get_last_crawled_pr_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'trenbe_crawled_pr_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('trenbe_crawled_pr_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롬 옵션 설정 함수
def init_chrome_options(ua):
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,960")
    chrome_options.add_argument(f"user-agent={ua}")
    return chrome_options

# 메인 실행 함수
def __main__():
    try:
        # 로그 파일 초기화
        init_log(LOG_FILE)

        # UserAgent 설정
        ua = UserAgent()
        ua.browsers.remove('chrome')
        ua = ua.random

        # 데이터베이스 연결 및 커서 생성
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 마지막으로 크롤링된 상품 ID 가져오기
        last_crawled_pr_id = get_last_crawled_pr_id(cur)

        # 크롤링할 상품 가져오기
        crawling_product = fetch_crawling_products(cur, last_crawled_pr_id)

        # 크롬 옵션 및 드라이버 초기화
        chrome_options = init_chrome_options(ua)
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
        driver.execute_cdp_cmd('Network.enable', {})

        # 로그인 수행
        driver.get('https://www.trenbe.com/login/email')
        time.sleep(2)
        inputs = driver.find_elements(By.CSS_SELECTOR, ".form-control")
        inputs[0].send_keys(crawling_id)
        inputs[1].send_keys(crawling_pw)
        driver.find_element(By.XPATH, "//*[@id='container']/div/div/div[2]/button").click()
        time.sleep(2)

        # 크롤링할 상품이 없으면 config 정보 삭제
        if len(crawling_product) < 1:
            cur.execute('delete from config where cfg_key="trenbe_crawled_pr_id"')
            conn.commit()

        brand_keyword = ''
        for idx, product in enumerate(crawling_product):
            product_found = False

            # 브랜드 검색
            if brand_keyword != product['b_search_keyword']:
                driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
                time.sleep(2)

                driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(product['b_search_keyword'])
                time.sleep(1)
                driver.find_element(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1').click()
                time.sleep(3)
                brand_keyword = product['b_search_keyword']

                driver.execute_script('window.scrollTo(0, 180);')

            driver.find_element(By.CSS_SELECTOR, '.input-wrap > input').send_keys(product['pr_name'])
            scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')

            # 페이지 스크롤
            for i in range(1, 2, 3):
                scrollY = 4000
                driver.execute_script(f'arguments[0].scrollTo(0, {scrollY});', scrollItem)
                time.sleep(2)

            # 상품 검색 결과에서 클릭
            driver_product_list = driver.find_elements(By.CSS_SELECTOR, '.StepItemList__ListContainer-sc-4a1pi5-1 > div')
            for driver_product in driver_product_list:
                if driver_product.text.find(product['pr_name']) > -1:
                    product_found = True

                    # 상품 클릭 및 상세 정보 크롤링
                    scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
                    driver.execute_script(f'arguments[0].scrollTo(0, {driver_product.location["y"]});', scrollItem)
                    time.sleep(2)

                    driver.execute_script("arguments[0].click();", driver_product)
                    time.sleep(2)

                    driver_product_detail = driver.find_elements(By.CSS_SELECTOR, '.ConfirmModal__DataLineContainer-sc-1brpfr9-5 dd')

                    category = driver_product_detail[0].text
                    brand = driver_product_detail[1].text
                    pr_detail_name = driver_product_detail[2].text

                    if driver_product.text.find('바로시세') == -1:
                        break

                    driver.find_element(By.CSS_SELECTOR, '.ConfirmModal__ConfirmModalWrap-sc-1brpfr9-0 button.confirm').click()
                    time.sleep(1)

                    try:
                        s = driver.find_elements(By.CSS_SELECTOR, '.Modal__ModalFooter-n8rj83-5 button')[1].click()
                        time.sleep(1)
                    except:
                        pass

                    # 시세 정보 크롤링
                    soup = BeautifulSoup(driver.page_source, 'html.parser')
                    tds = soup.select('.SiseContents__PriceTable-sc-1vnoo68-5 td')

                    avg_sale = re.sub(r'[,\s원-]', '', tds[1].text.strip())
                    avg_buy = re.sub(r'[,\s원-]', '', tds[2].text.strip())
                    max_sale = re.sub(r'[,\s원-]', '', tds[4].text.strip())
                    max_buy = re.sub(r'[,\s원-]', '', tds[5].text.strip())

                    cur.execute('update product_resale set pr_category=%s, pr_update_datetime=%s, pr_avg_sale=%s, pr_avg_buy=%s, pr_max_sale=%s, pr_max_buy=%s where pr_id = %s', (category, datetime.now(), avg_sale, avg_buy, max_sale, max_buy, product['pr_id']))
                    cur.execute('update config set cfg_value = %s where cfg_key = "trenbe_crawled_pr_id"', (product['pr_id']))
                    conn.commit()

                    driver.back()
                    time.sleep(1)
                    break

            if not product_found:
                driver.refresh()
                time.sleep(2)

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, err)
    finally:
        driver.quit()
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
