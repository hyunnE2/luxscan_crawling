from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import traceback
import pymysql
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 로드
load_dotenv()

# 데이터베이스 설정 정보 로드
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 경로 설정 및 로그 파일
SAVE_PATH = os.environ.get('SAVE_PATH') + 'trenbe/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'usedProductGetCrawlingBrandList.log'

# 로그 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 기록 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 데이터베이스에서 브랜드 정보를 가져오는 함수
def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 2')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        # 브랜드 이름에서 공백 제거 후 키로 사용
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']
    return brands

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

# 메인 실행 함수
def __main__():
    try:
        # 로그 파일 초기화
        init_log(LOG_FILE)

        # 데이터베이스 연결 및 커서 생성
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 데이터베이스에서 브랜드 정보 가져오기
        brands = fetch_brand(cur)

        # 크롬 옵션 초기화 및 드라이버 생성
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        # 대상 URL로 이동
        driver.get('https://www.trenbe.com/resale/product-registration/brand?stepName=BRAND')
        time.sleep(2)

        # 페이지 스크롤 설정 및 실행
        scrollItem = driver.find_element(By.CSS_SELECTOR, '.StepItemList__StepItemListWrap-sc-4a1pi5-0')
        driver.execute_script('window.scrollTo(0, 600);')
        tmp = -1
        scrollY = 0
        while tmp != scrollY:
            scrollY += 20000
            tmp = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            time.sleep(4)
            scrollY += 20000
            scrollY = driver.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)

        time.sleep(2)

        # 페이지 소스 파싱
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        brand_list = soup.select('.StepItemList__ListContainer-sc-4a1pi5-1 > div')

        # 브랜드 정보 처리 및 데이터베이스에 삽입
        for brand in brand_list:
            brand_eng = brand.select_one('span').text
            brand_kr = brand.text.replace(brand_eng, '')

            # 브랜드가 데이터베이스에 없을 경우 삽입
            b_id = brands.get(brand_eng.replace(' ', ''))
            if b_id is None:
                cur.execute('insert into brand(`m_id`, `b_name`, `b_search_keyword`) values(2, %s, %s)', (brand_eng, brand_kr))
                cur.execute('select * from brand order by b_id desc limit 1')
                b_id = cur.fetchone()['b_id']

            # 크롤링 목록에 삽입
            cur.execute('insert ignore into crawling_product_list(`m_id`, `b_id`) values(2, %s)', (b_id))
            conn.commit()

    except Exception:
        # 예외 처리 및 로그 작성
        err = traceback.format_exc()
        print(err)
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        # 데이터베이스 연결 종료 및 로그 기록
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
