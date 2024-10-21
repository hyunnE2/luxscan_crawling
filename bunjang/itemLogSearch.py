import time
import traceback
import pymysql
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os
import json

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
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 마지막으로 크롤링한 제품 ID를 DB에서 가져오는 함수
def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'bunjang_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('bunjang_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 제품 목록을 가져오는 함수
def fetch_bunjang_products(cur, last_crawled_p_id, p_count=1, limit=100):
    cur.execute(f"SELECT * FROM bunjang_product WHERE m_id = 6 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} and p_is_possible_crawling = 1 LIMIT {limit}")
    return cur.fetchall()

# 카테고리를 DB에서 가져오는 함수
def fetch_category(cur):
    cur.execute('select * from category where m_id = 6')
    tmp_categories = cur.fetchall()
    categories = {}
    for category in tmp_categories:
        categories[category['c_name']] = category['c_id']
    return categories

# 등급을 DB에서 가져오는 함수
def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 6')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    return grades

# 중고 상품 정보를 업데이트하고, 판매 내역을 기록하는 함수
def update_used_product(cur, product, is_selled):
    cur.execute('update used_product set b_id=%s, p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s',
                (product['b_id'], 0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into used_product_sell_history(`p_id`, `g_id`, `psh_sold_datetime`, `psh_price`) values(%s, %s, %s, %s)',
                    (product['p_id'], product['g_id'], datetime.now(), product['p_price']))

# 메인 크롤링 함수
def __main__():
    try:
        # 로그 초기화
        init_log(LOG_FILE)

        # DB 연결 설정
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 카테고리 및 등급 정보 가져오기
        categories = fetch_category(cur)
        grades = fetch_grade(cur)

        # 마지막으로 크롤링한 p_id 가져오기
        last_crawled_p_id = get_last_crawled_p_id(cur)

        # 크롤링할 제품 목록 가져오기
        products = fetch_bunjang_products(cur, last_crawled_p_id, p_count=0)

        # 크롤링할 제품이 없는 경우
        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'bunjang_crawled_p_id'")
            write_log(LOG_FILE, 'not found products')
            conn.commit()

        # 각 제품에 대한 크롤링 처리
        for product in products:
            rq_status = False  # 요청 성공 여부

            # 제품의 URL에서 modelId 추출
            m_id = product['p_url'].split('/')[-1]

            # API 요청하여 제품 정보 가져오기
            response = requests.get(f'https://api.bunjang.co.kr/api/catalog/v1/products?modelId={m_id}&size=20')

            if response.status_code != 200:
                write_log(LOG_FILE, f"break : status code is {response.status_code}")
                break

            data = json.loads(response.content)
            total_pages = data['totalPages']  # 총 페이지 수
            total_elements = data['totalElements']  # 총 아이템 수

            crawled_list = []  # 크롤링한 데이터를 저장할 리스트

            # 각 페이지의 제품 정보를 반복해서 가져옴
            for i in range(total_pages):
                response = requests.get(f'https://api.bunjang.co.kr/api/catalog/v1/products?modelId={m_id}&page={i}&quickDelivery=false&size=20&sort=date&status=SELLING&status=RESERVED')

                if response.status_code != 200:
                    write_log(LOG_FILE, f"break : status code is {response.status_code}")
                    rq_status = True
                    break

                data = json.loads(response.content)['data']

                # 각 제품 항목을 처리
                for item in data:
                    parent_c_id = None  # 부모 카테고리 ID
                    brows_cates = item['categoryName'].split('>')  # 카테고리 이름 추출
                    grade = item['productConditionDesc'].strip()  # 제품 상태 (등급)

                    # 새로운 등급이 발견되면 등급 테이블에 추가
                    if grades.get(grade) is None:
                        cur.execute('insert into `grade`(`m_id`, `g_market_grade`) values(6, %s)', (grade))
                        cur.execute('select * from `grade` where `g_market_grade` = %s', (grade))
                        grades[grade] = cur.fetchone()['g_id']

                    # 각 카테고리를 처리
                    for brows_cate in brows_cates:
                        swap_cate = brows_cate.strip()

                        if categories.get(swap_cate):
                            cate = categories.get(swap_cate)
                        else:
                            cur.execute('insert into `category`(`m_id`, `c_parent_id`, `c_name`) values(6, %s, %s)', (parent_c_id, swap_cate))
                            cur.execute('select * from `category` where `c_name` = %s', (swap_cate))
                            cate = cur.fetchone()

                            categories[cate['c_name']] = cate['c_id']
                            cate = cate['c_id']

                        parent_c_id = cate

                    # 크롤링 데이터를 리스트에 추가
                    crawled_list.append((
                        6,  # 마켓 ID
                        cate,  # 카테고리 ID
                        product['b_id'],  # 브랜드 ID
                        grades[grade],  # 등급 ID
                        item['productTitle'],  # 제품명
                        item['productPrice'],  # 가격
                        'https://m.bunjang.co.kr/products/' + str(item['pid']),  # 제품 URL
                        item['productImage'],  # 제품 이미지 URL
                        item['productCreatedAt'],  # 제품 생성 시간
                        item['productUpdatedAt'],  # 제품 업데이트 시간
                        datetime.now()  # 마지막 크롤링 시간
                    ))

                # 크롤링된 데이터를 DB에 삽입 또는 업데이트
                for crawled_data in crawled_list:
                    cur.execute(
                        'insert into used_product(`m_id`,`c_id`,`b_id`,`g_id`,`p_name_kr`,`p_price`,`p_url`,`p_img_url`,`p_created_datetime`,`p_updated_datetime`,`p_last_crawling_datetime`) '
                        'values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();',
                        crawled_data
                    )

            if rq_status:
                break

    except Exception:
        # 오류 발생 시 로그에 기록
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error Location : page:{i+1}, modelId:{m_id}")
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        # DB 연결 종료 및 로그 작성
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 실행
if __name__ == "__main__":
    __main__()
