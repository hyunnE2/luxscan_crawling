import time
import traceback
import pymysql
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from dotenv import load_dotenv
import os

# 환경 변수 파일 로드
load_dotenv()

# 데이터베이스 연결 설정 정보
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 파일 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'koibito/'
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
LOG_FILE = SAVE_PATH + 'itemLogSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# 로그 기록 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 마지막으로 크롤링된 상품 ID 가져오기
def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'koibito_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('koibito_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 상품 데이터 가져오기
def fetch_used_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM used_product WHERE m_id = 3 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} AND p_is_possible_crawling=1 LIMIT {limit}")
    return cur.fetchall()

# 브랜드 데이터 가져오기
def fetch_brand(cur):
    cur.execute('SELECT * FROM brand WHERE m_id = 3')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '').upper()] = brand['b_id']
    return brands

# 중고 상품 업데이트 함수
def update_used_product(cur, product, is_selled):
    cur.execute('UPDATE used_product SET b_id=%s, p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s WHERE p_id=%s', 
                (product['b_id'], 0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('INSERT INTO used_product_sell_history(p_id, g_id, psh_sold_datetime, psh_price) VALUES(%s, %s, %s, %s)', 
                    (product['p_id'], product['g_id'], datetime.now(), product['p_price']))

# 메인 크롤링 함수
def __main__():
    try:
        # 로그 초기화
        init_log(LOG_FILE)
        
        # DB 연결
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 브랜드 데이터 가져오기
        brands = fetch_brand(cur)

        # 마지막 크롤링된 상품 ID 가져오기
        last_crawled_p_id = get_last_crawled_p_id(cur)
        
        # 크롤링할 상품 데이터 가져오기
        products = fetch_used_products(cur, last_crawled_p_id, p_count=0)
        
        if len(products) < 1:
            cur.execute("UPDATE config SET cfg_value = 0 WHERE cfg_key = 'koibito_crawled_p_id'")
            write_log(LOG_FILE, 'not found products')
            conn.commit()
        
        # 각 상품에 대해 크롤링 시작
        for product in products:
            response = requests.get(product['p_url'])
            if response.status_code != 200:
                write_log(LOG_FILE, f"break : status code is {response.status_code}")
                break

            # HTML 파싱
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 상품이 존재하지 않는 경우 확인
            if response.text.find('해당 상품이 존재하지 않습니다.') > -1:
                update_used_product(cur, product, True)
                write_log(LOG_FILE, '존재하지 않는 상품')
                continue

            # 이미지 URL 수집
            imgs = soup.select('center> table:nth-child(7) > form > tr > td > table > tr > td > div > table > tr > td:nth-child(1) > table > tr:nth-child(2) img')
            product['img_urls'] = ','.join([img['src'] for img in imgs])

            # 브랜드 정보 추출
            brand = soup.select(".detail_info_list > .info_list_basic > dd")[0].text.strip()
            brand = brand[:brand.find('(')]
            upper_brand = brand.replace(' ', '').upper()

            # 브랜드가 존재하지 않으면 추가
            if brands.get(upper_brand) is None:
                cur.execute(f"INSERT INTO brand(m_id, b_name, b_search_keyword) VALUES (3, '{brand}', '{brand}')")
                cur.execute("SELECT * FROM brand WHERE m_id = 3 ORDER BY b_id DESC LIMIT 1")
                b_id = cur.fetchone()['b_id']
                brands[upper_brand] = b_id
                product['b_id'] = b_id
            else:
                product['b_id'] = brands[upper_brand]

            # 품절 여부 확인
            is_sold_out = soup.select_one(".detail_info_title > .info_price").text
            if is_sold_out.find('품절') > -1:
                update_used_product(cur, product, True)
                write_log(LOG_FILE, f"sold out p_id : {product['p_id']}")
            else:
                update_used_product(cur, product, False)
                write_log(LOG_FILE, f"exists p_id : {product['p_id']}")

            # 크롤링된 마지막 ID 업데이트
            cur.execute("UPDATE config SET cfg_value = %s WHERE cfg_key = 'koibito_crawled_p_id'", (product['p_id']))
            conn.commit()

    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        # DB 연결 종료
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

# 메인 함수 실행
if __name__ == "__main__":
    __main__()
