import requests
import json
import pymysql
import traceback
from datetime import datetime
from py_mini_racer import py_mini_racer
from dotenv import load_dotenv
import os
from fake_useragent import UserAgent

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

# 로그 파일 및 크롤링 데이터 저장 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'kream/'
LOG_FILE = SAVE_PATH + 'itemOptionSearch.log'

# 로그 파일 초기화 함수
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start bot3 at : {datetime.now()}\n')

# 로그 작성 함수
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

# 마지막으로 크롤링된 제품 ID 가져오는 함수
def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'kream_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('kream_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# 크롤링할 제품을 가져오는 함수
def fetch_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM product WHERE m_id = 1 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

# 마지막으로 크롤링된 제품 ID 업데이트 함수
def update_last_crawled_p_id(cur, p_id):
    cur.execute(f"UPDATE config SET cfg_value = {p_id} WHERE cfg_key = 'kream_crawled_p_id'")

# HTML에서 스크립트 데이터를 추출하는 함수
def extract_script_content(html_content):
    script_start = html_content.find("window.__NUXT__=")
    script_end = html_content.find("</script>", script_start)
    if script_start == -1 or script_end == -1:
        return None
    return html_content[script_start:script_end]

# py_mini_racer를 사용하여 nuxt 데이터를 파싱하는 함수
def parse_nuxt_data(script_content):
    ctx = py_mini_racer.MiniRacer()
    ctx.eval("window={};")
    ctx.eval(script_content)
    try:
        return ctx.eval("JSON.stringify(window.__NUXT__.pinia.product.response.sales_options)")
    except:
        return ctx.eval("JSON.stringify(window.__NUXT__.pinia.product.response.sale_info.details.options)")

# 상품 가격 정보를 삽입하거나 업데이트하는 함수
def upsert_product_prices(cur, product_id, items):
    for item in items:
        if 'is_show_option_price' in item and not item['is_show_option_price']:
            continue

        price = item.get('price', item.get('lowest_normal', 0))
        fast_price = item.get('lowest_100', 0)
        option = item.get('key', item.get('option', ''))

        cur.execute(
            """
            INSERT INTO price_by_option_of_product(p_id, pboop_option, pboop_price, pboop_quick_price) 
            VALUES (%s, %s, %s, %s)
            ON DUPLICATE KEY UPDATE 
                pboop_price = VALUES(pboop_price), 
                pboop_quick_price = VALUES(pboop_quick_price), 
                pboop_datetime = %s
            """,
            (product_id, option, price, fast_price, datetime.now())
        )

# 각 제품을 처리하는 함수
def process_product(session, product, cur, ua, headers):
    response = session.get(product['p_url'], headers=headers)
    if response.status_code != 200:
        write_log(LOG_FILE, "status_code = " + str(response.status_code))
        write_log(LOG_FILE, "error url = " + response.url)
        return False, product['p_id'], response.status_code

    script_content = extract_script_content(response.text)
    if script_content is None:
        write_log(LOG_FILE, "script not found")
        return False, product['p_id'], 200

    nuxt_data = parse_nuxt_data(script_content)
    if nuxt_data is None:
        write_log(LOG_FILE, "failed to parse nuxt data")
        return False, product['p_id'], 200

    upsert_product_prices(cur, product['p_id'], json.loads(nuxt_data))
    write_log(LOG_FILE, f"success. p_id : {product['p_id']}")
    return True, product['p_id'], 200

# 메인 크롤링 함수
def main():
    ua = UserAgent()
    ua.browsers.remove('chrome')

    init_log(LOG_FILE)
    session = requests.Session()

    try:
        # 데이터베이스 연결 설정
        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        # 마지막으로 크롤링한 p_id 가져오기
        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id)
        write_log(LOG_FILE, f"bot3 : loaded products {len(products)}")

        headers = {'user-agent': ua.random}

        # 크롤링할 제품이 없으면 설정 초기화
        if len(products) < 1:
            cur.execute("DELETE FROM config WHERE cfg_key = 'kream_crawled_p_id'")
            conn.commit()
            write_log(LOG_FILE, f"bot3 : deleted kream_crawled_p_id")

        # 각 제품을 처리
        for i, product in enumerate(products):
            if i % 400 == 0:
                headers = {'user-agent': ua.random}
            success, p_id, code = process_product(session, product, cur, ua, headers)
            if not success:
                update_last_crawled_p_id(cur, p_id - 1)
                if code == 404:
                    update_last_crawled_p_id(cur, p_id)
                    conn.commit()
                    continue
                break

            update_last_crawled_p_id(cur, p_id)
            write_log(LOG_FILE, f"p_id : {p_id} end at :{datetime.now()}")
            conn.commit()

    except Exception:
        # 오류 발생 시 로그에 기록
        err = traceback.format_exc()
        write_log(LOG_FILE, f'error bot3 : {err}')

    finally:
        # 세션 및 데이터베이스 연결 종료
        write_log(LOG_FILE, f'ended bot3 at : {datetime.now()}')
        session.close()
        conn.close()

# 메인 실행
if __name__ == "__main__":
    main()
