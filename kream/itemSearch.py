import time
import traceback
import pymysql
import re

from selenium import webdriver
from selenium.webdriver.common.keys import Keys

from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

# 환경 변수를 로드
load_dotenv()

# URL과 DB 설정을 환경 변수에서 불러옴
base_url = os.environ.get('KREAM_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

# 크롤링 데이터 저장 경로 설정
SAVE_PATH = os.environ.get('SAVE_PATH') + 'kream/'

# 드라이버 종료 함수
def quitDriver(driver):
    try:
        driver.close()
    except Exception:
        pass
    try:
        driver.quit()
    except Exception:
        pass

# 로그 파일을 작성
file = open(SAVE_PATH + 'itemSearch.log', 'a', encoding='euc-kr')
file.write(f'start bot1 at : {datetime.now()}\n')

# 데이터베이스 연결 설정
conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor(pymysql.cursors.DictCursor)

# 크롬 드라이버 옵션 설정
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

# 크롬 드라이버 초기화
exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')
driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})

try:
    # 브랜드 및 카테고리 정보 가져오기
    cur.execute('SELECT b_id, b_name FROM brand WHERE b_super_id IS NULL')
    brands = cur.fetchall()

    cur.execute('SELECT c_id, c_keyword, c_name, c_is_men, c_is_women FROM category WHERE m_id = 1')
    categories = cur.fetchall()

    # 각 브랜드 및 카테고리 별로 데이터 수집
    for brand in brands:
        cur.execute(f'SELECT * FROM product WHERE b_id = {brand["b_id"]} AND m_id = 1')
        tmp = cur.fetchall()
        exist_products = {}
        for exist_product in tmp:
            exist_products[exist_product['p_url']] = {'p_id': exist_product['p_id'], 'p_count': exist_product['p_count']}

        for category in categories:
            for gender in ('men', 'women'):
                items = {}

                # 해당 성별에 카테고리가 없으면 스킵
                if category['c_is_' + gender] == 0:
                    continue

                # 해당 카테고리와 성별에 맞는 URL에서 데이터 수집
                driver.get(f'https://kream.co.kr/brands/{brand["b_name"]}?gender={gender}&shop_category_id={category["c_keyword"]}&sort=popular_score')
                file.write(f'bot1 get_url : https://kream.co.kr/brands/{brand["b_name"]}?gender={gender}&shop_category_id={category["c_keyword"]}&sort=popular_score\n')
                time.sleep(2)

                last_height = driver.execute_script("return document.body.scrollHeight")
                while True:
                    # 페이지 스크롤
                    old_height = driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    body = driver.find_element_by_css_selector('body')
                    body.send_keys(Keys.ARROW_UP)
                    time.sleep(3)
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    if new_height == last_height:
                        break
                    last_height = new_height

                soup = BeautifulSoup(driver.page_source, 'html.parser')
                time.sleep(4)

                # 제품 정보를 가져옴
                driver_items = soup.select('.search_result_list > .search_result_item')
                file.write(f'search products : {len(driver_items)}, document scrollHeight : {last_height}\n')

                # HTML과 JS ITEM을 결합하는 과정임
                # 각각에서만 들고올 수 있는 데이터가 있어서 해당 코드가 필요함

                # --- 시작 지점 ---
                for driver_item in driver_items:
                    item_id = driver_item.select_one('.product_card > .item_inner')['href'].replace('/products/', '').replace(' ', '')
                    items[item_id] = {
                        'name': driver_item.select_one('.product_info_product_name > .name').text,
                        'market_id': 1,
                        'brand_id': brand["b_id"],
                        'kr_name': driver_item.select_one('.product_info_product_name > .translated_name').text,
                        'price': re.sub(r'[,\s원-]', '', driver_item.select_one('.price > .amount').text)
                    }
                    
                    discount_rate = driver_item.select_one('.price > .amount > .discount_rate')
                    if discount_rate:
                        items[item_id]['price'] = items[item_id]['price'].replace(discount_rate.text, '')
                    items[item_id]['price'] = int(items[item_id]['price']) if items[item_id]['price'] != "" else 0
                    items[item_id]['url'] = base_url + driver_item.select_one('.item_inner')['href']
                    items[item_id]['img_url'] = driver_item.select_one('.product_img > img')['src']

                try:
                    js_items = driver.execute_script("return window.__NUXT__.pinia['search-tab']['productFeed']['items']")
                    file.write(f'js items : {len(js_items)}\n')
                except Exception:
                    file.write(f'bot1 : not found js_items\n')
                    continue
                
                
                for js_item in js_items:
                    item_id = str(js_item['product']['release']['id'])
                    items[item_id]['origin_price'] = js_item['product']['release']['original_price']
                    items[item_id]['sales'] = js_item['product']['market']['total_sales']
                    items[item_id]['option'] = ','.join(js_item['product']['options'])
                    items[item_id]['img_url'] = ','.join(js_item['product']['release']['image_urls'])
                    items[item_id]['model_number'] = js_item['product']['release']['style_code']
                    items[item_id]['color'] = js_item['product']['release']['colorway']
                # --- 종료 지점 ---


                # 수집된 아이템을 데이터베이스에 삽입 또는 업데이트
                for item in items:
                    tmp = items[item]
                    result = exist_products.get(tmp['url'], None)
                    before_sales = 0

                    sql = """
                        INSERT INTO product (m_id, b_id, c_id, g_id, p_name, p_name_kr, p_price, p_origin_price, p_count, p_option, p_model_number, p_color, p_url, p_img_url) 
                        VALUES (%s, %s, %s, 1, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

                    # 크롤링한 리스트에 새로운 제품을 추가하고 DB에 삽입
                    if result is None:
                        cur.execute(sql, (
                            tmp['market_id'], tmp['brand_id'], category['c_id'], tmp['name'], tmp['kr_name'], 
                            tmp['price'], tmp['origin_price'], tmp['sales'], tmp['option'], tmp['model_number'], 
                            tmp['color'], tmp['url'], tmp['img_url']
                        ))
                        cur.execute('SELECT * FROM product ORDER BY p_id DESC')
                        prod = cur.fetchone()
                        exist_products[prod['p_url']] = {'p_id': prod['p_id'], 'p_count': prod['p_count']}
                        item_id = prod['p_id']
                    # 이미 존재하는 제품의 판매량이 업데이트된 경우 처리
                    else:
                        item_id = result['p_id']
                        sql = """
                            UPDATE product SET p_price = %s, p_count = %s, p_option = %s, p_last_crawling_datetime = %s 
                            WHERE p_id = %s
                        """
                        cur.execute(sql, (tmp['price'], tmp['sales'], tmp['option'], datetime.now(), item_id))
                        before_sales = result['p_count']

                    # 새로운 판매량이 있을 때만 크롤링 리스트에 추가
                    if before_sales != tmp['sales']:
                        if tmp['sales'] == '0':
                            continue
                        cur.execute('INSERT IGNORE INTO crawling_product_list(m_id, p_id) VALUES(1, %s)', (item_id))

                conn.commit()

            # 크롤링이 완료되면 브랜드 업데이트 시간 기록
            file.write(f'bot1 : {brand} {category} ended : {datetime.now()}\n')
            file.flush()
        
        # brand의 데이터로 로드 된 시간을 저장함 데이터가 너무 많아 실행되지 않는 브랜드를 체크하기 위함
        cur.execute(f'UPDATE brand SET b_update_at = "{datetime.now()}" WHERE b_id = "{brand["b_id"]}"')
        conn.commit

except Exception:
    # 오류 발생 시 로그에 기록
    err = traceback.format_exc()
    file.write(f'error bot1 : {err}\n')