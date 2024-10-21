import time
import traceback
import pymysql
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from datetime import datetime
from dotenv import load_dotenv
import os
import re

# 환경 변수를 로드
load_dotenv()

# DB 설정 값을 환경 변수에서 불러옴
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 로그 파일과 크롤링 데이터 저장 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'bunjang/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 브랜드 정보를 DB에서 가져오는 함수
def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 6')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_market_id']] = brand['b_id']
    return brands

# Chrome 드라이버 옵션 초기화 함수
def init_chrome_options():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")  # 백그라운드 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

    return chrome_options

# 페이지 스크롤 다운 함수
def scroll_down(driver):
    driver.find_element(By.TAG_NAME, "body").send_keys(Keys.END)
    time.sleep(2)  # 로딩 시간 대기

# 데이터를 스크래핑하는 함수
def scrape_data(url, driver):
    driver.get(url)
    products = []  # 스크래핑된 제품 정보를 담을 리스트
    last_height = driver.execute_script("return document.body.scrollHeight")  # 현재 페이지 높이 가져옴

    while True:
        scroll_down(driver)  # 페이지 스크롤 다운
        new_height = driver.execute_script("return document.body.scrollHeight")  # 스크롤 후의 높이 가져옴
        if new_height == last_height:  # 스크롤 전후 높이가 같다면 더 이상 스크롤할 필요 없음
            break
        last_height = new_height  # 이전 높이를 현재 높이로 업데이트

    # 아이템 요소를 가져옴 (CSS 셀렉터는 실제 HTML에 맞게 변경 필요)
    items = driver.find_elements(By.CSS_SELECTOR, "a.sc-cWSHoV.hovUBa")

    for item in items:
        try:
            # 각 제품의 정보 추출 (클래스 이름은 실제 HTML 구조에 맞게 수정)
            name = item.find_element(By.CLASS_NAME, "sc-fhzFiK").text  # 제품명
            price = item.find_element(By.CLASS_NAME, "sc-lcIPJg").text  # 가격
            price = re.sub(r'[,\s원-]', '', price.strip())  # 가격 문자열에서 원, 쉼표 제거
            price = 0 if price == '' else price.replace('만', '0000')  # 가격이 만원 단위라면 변환

            img_url = item.find_element(By.CSS_SELECTOR, "img.sc-kOPcWz.elHqEV").get_attribute("src")  # 제품 이미지 URL
            transaction_count = item.find_element(By.CLASS_NAME, "sc-kdBSHD").text  # 거래 횟수
            result = re.sub(r'거래|건', '', transaction_count.strip())  # 거래/건 제거
            result = re.sub(r'\s+', '', result).replace('만', '0000')  # 거래 횟수를 변환

            product_url = item.get_attribute("href")  # 제품 URL

            # 제품 정보를 리스트에 추가
            products.append({
                "url": product_url,
                "name": name,
                "price": price,
                "img_url": img_url,
                "transaction_count": result
            })

        except Exception:
            # 오류가 발생하면 로그에 기록
            err = traceback.format_exc()
            write_log(LOG_FILE, f"Error: {err}")

    return products  # 스크래핑한 제품 정보 반환

# Chrome 드라이버 종료 함수
def quitDriver(driver):
    try:
        driver.close()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass

# 메인 크롤링 함수
def __main__():
    try:
        init_log(LOG_FILE)  # 로그 초기화
        conn = pymysql.connect(**DB_CONFIG)  # DB 연결 설정
        cur = conn.cursor(pymysql.cursors.DictCursor)

        brands = fetch_brand(cur)  # 브랜드 정보 가져오기

        # Chrome 드라이버 설정 및 초기화
        chrome_options = init_chrome_options()
        driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
        driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
        driver.execute_cdp_cmd('Network.enable', {})

        # 각 브랜드에 대해 데이터 수집
        for brand_id in brands.keys():
            url = f"https://inspection-auth.bunjang.co.kr/showcase/app-keyword/brands?id={brand_id}&category="
            data = scrape_data(url, driver)  # 스크래핑 함수 호출

            # 수집된 데이터를 DB에 삽입
            sql = """
                INSERT INTO bunjang_product (m_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_img_url, p_last_crawling_datetime)
                VALUES (6, %s, %s, %s, %s, 0, %s, 0, %s, NOW())
                ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """

            for item in data:
                cur.execute(sql, (brands[brand_id], item['name'], item['price'], item['url'], item['transaction_count'], item['img_url']))
                write_log(LOG_FILE, f"{brands[brand_id]}, {item['name']}, {item['price']}, {item['url']}, {item['transaction_count']}, {item['img_url']}")
                conn.commit()  # DB에 커밋

    except Exception:
        # 오류 발생 시 로그에 기록
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")

    finally:
        # DB 연결 종료 및 드라이버 종료
        conn.close()
        quitDriver(driver)
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 실행
if __name__ == "__main__":
    __main__()
