import requests
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 파일 로드
load_dotenv()

# 기본 URL 및 데이터베이스 연결 설정 정보
base_url = os.environ.get('KOIBITO_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 파일 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'koibito/'
LOG_FILE = SAVE_PATH + 'itemSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 기록 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 등급 데이터 가져오기
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 3')
    return cur.fetchall()

try:
    # 데이터베이스 연결
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)  # 로그 파일 초기화

    # 등급 데이터 로드
    tmp_grades = fetch_grade(cur)
    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    # 크롤링할 URL 설정 및 초기 페이지 번호
    url = f'{base_url}/update_goods.html'
    i = 1

    while True:
        # 페이지 요청
        response = requests.get(url + '?page=' + str(i))
        if response.status_code != 200:
            write_log(LOG_FILE, f"break : status code is {response.status_code}")
            break

        # HTML 파싱
        soup = BeautifulSoup(response.content, 'html.parser')
        products = soup.select('#product_list > ul > li')

        # 상품이 없는 경우 처리
        if len(products) < 1:
            if i == 1:
                write_log(LOG_FILE, f'not found products')
            break
        else:
            write_log(LOG_FILE, f"loaded product count : {len(products)}")

        # 각 상품에 대해 처리
        for product in products:
            tables = product.select('table')
            p_url = product.select_one('a')['href']
            name = re.sub(r'[,\s원-]', '', tables[0].text.strip())  # 상품 이름에서 특수문자 제거
            tds = tables[1].select('td')

            # 등급 정보 추출 및 등급 ID 확인
            grade = re.sub(r'[\s]', '', tds[0].text.strip())
            g_id = grades.get(grade)
            if g_id is None:
                # 등급이 존재하지 않을 경우 추가
                cur.execute('insert into `grade`(`m_id`, `g_market_grade`) values(3, %s)', (grade))
                cur.execute('select * from `grade` where `g_market_grade` = %s', (grade))
                g_id = cur.fetchone()['g_id']
                grades[grade] = g_id

            # 가격 정보 추출
            price = re.sub(r'[,\s원-]', '', tds[1].text.strip())

            # 거래 진행중 여부 확인
            if price.find('거래진행중') > -1:
                price = -1
                write_log(LOG_FILE, f"inserst used_product")

            # 상품 정보를 데이터베이스에 삽입 또는 업데이트
            sql = """
            INSERT INTO used_product (m_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
            VALUES (3, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
            ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """
            cur.execute(sql, (g_id, name, price, base_url + '/' + p_url))
            conn.commit()

        # 다음 페이지로 이동
        i += 1

except Exception as e:
    # 예외 처리 및 로그 기록
    write_log(LOG_FILE, f"Error: {e}")

finally:
    # 데이터베이스 연결 종료 및 로그 기록
    conn.close()
    write_log(LOG_FILE, f"End at: {datetime.now()}")
