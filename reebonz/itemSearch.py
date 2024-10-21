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

# 환경 변수 로드
load_dotenv()

# 베이스 URL 설정
base_url = os.environ.get('REEBONZ_URL')

# 데이터베이스 설정
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 로그 파일 경로와 저장 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH')+'reebonz/'
LOG_FILE = SAVE_PATH+'itemSearch.log'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

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

# 브랜드를 데이터베이스에서 가져오는 함수
def fetch_brand(cur):
    """
    데이터베이스에서 m_id가 5인 브랜드 정보를 가져와서 딕셔너리 형태로 반환합니다.
    """
    cur.execute('select * from brand where m_id = 5')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '').upper()] = brand['b_id']
    
    return brands

# 등급을 데이터베이스에서 가져오는 함수
def fetch_grade(cur):
    """
    데이터베이스에서 m_id가 5인 등급 정보를 가져와서 딕셔너리 형태로 반환합니다.
    """
    cur.execute('select * from grade where m_id = 5')
    tmp_grades = cur.fetchall()
    
    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']
    
    return grades

# 크롬 옵션 초기화 함수
def init_chrome_options(ua):
    """
    크롬 드라이버의 옵션을 설정합니다.
    """
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")  # 브라우저를 숨김 모드로 실행
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument(f"user-agent={ua}")
    return chrome_options

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

# 메인 코드 실행 부분
try:
    # 사용자 에이전트를 초기화합니다.
    ua = UserAgent()
    ua.browsers.remove('chrome')  # Chrome 사용자 에이전트를 목록에서 제거
    ua = ua.random  # 무작위로 사용자 에이전트 생성

    # 데이터베이스 연결
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    # 로그 파일 초기화
    init_log(LOG_FILE)

    # 데이터베이스에서 브랜드 및 등급 정보 가져오기
    brands = fetch_brand(cur)
    grades = fetch_grade(cur)

    # 크롬 드라이버 초기화
    chrome_options = init_chrome_options(ua)
    driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
    driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": ua})
    driver.execute_cdp_cmd('Network.enable', {})

    # 크롤링할 URL 설정
    url = f'{base_url}/events/28635'
    driver.get(url)
    time.sleep(4)

    # 페이지 끝까지 스크롤
    last_height = driver.execute_script("return document.body.scrollHeight")
    new_height = 0
    while True:
        while new_height < last_height:
            driver.execute_script("window.scrollBy(0, 400);")
            time.sleep(0.2)  # 필요에 따라 대기 시간 조정
            new_height = driver.execute_script("return window.scrollY + window.innerHeight") + 300

        # "더 보기" 버튼 클릭 시 더 많은 항목을 로드
        try:
            btn = driver.find_element(By.CSS_SELECTOR, "button.btn.btn--more")
            driver.execute_script("arguments[0].click();", btn)
            time.sleep(3)
            last_height = driver.execute_script("return document.body.scrollHeight") + 300
        except NoSuchElementException:
            write_log(LOG_FILE, 'not search more button')
            break

    # BeautifulSoup을 사용해 페이지 HTML 파싱
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    products = soup.select('.products-list__grid2 > div')

    # 제품이 없는 경우 로그에 기록
    if len(products) < 1:
        write_log(LOG_FILE, f'not found products')
    else:
        write_log(LOG_FILE, f"loaded product count : {len(products)}")

        # 각 제품 정보 처리
        for product in products:
            p_url = product.select_one('a')['href']
            brand = product.select_one('.first-desc').text
            grade = product.select_one('.img-box').text

            # 등급 정보 처리
            g_id = grades.get(grade)
            if g_id is None:
                cur.execute('insert into `grade`(`m_id`, `g_market_grade`) values(5, %s)', (grade))
                cur.execute('select * from `grade` where `g_market_grade` = %s', (grade))
                g_id = cur.fetchone()['g_id']
                grades[grade] = g_id

            # 제품 이름과 가격 정보 처리
            name = product.select_one('.product-name').text
            price = re.sub(r'[,\s원-]', '', product.select_one('.price').text.strip())

            # 브랜드 정보 처리
            upper_brand = brand.replace(' ', '').upper()
            if brands.get(upper_brand) is None:
                cur.execute(f"insert into brand(`m_id`, `b_name`, `b_search_keyword`) values (5, '{brand}', '{brand}')")
                cur.execute("select * from brand where m_id = 5 order by b_id desc limit 1")
                b_id = cur.fetchone()['b_id']
                brands[upper_brand] = b_id
            else:
                b_id = brands.get(upper_brand)

            # 제품 정보 데이터베이스에 저장
            sql = """
            INSERT INTO used_product (m_id, g_id, b_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
            VALUES (5, %s, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
            ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """
            cur.execute(sql, (g_id, b_id, name, price, base_url + p_url))
            conn.commit()

except Exception as e:
    # 예외 발생 시 로그에 오류 기록
    write_log(LOG_FILE, f"Error: {e}")

finally:
    # 데이터베이스 및 드라이버 종료
    conn.close()
    quitDriver(driver)
    write_log(LOG_FILE, f"End at: {datetime.now()}")
