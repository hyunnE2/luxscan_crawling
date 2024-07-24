import time
import traceback
import pymysql
import re

from selenium import webdriver

from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('KREAM_URL')

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'kream/'

file = open(SAVE_PATH+'itemSearch.log', 'a', encoding='euc-kr')
file.write(f'start bot1 at : {datetime.now()}\n')

conn = pymysql.connect(**DB_CONFIG)
cur = conn.cursor(pymysql.cursors.DictCursor)

## login 
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920,1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})

try:
    cur.execute('select b_id, b_name from brand where b_super_id is NULL')
    brands = cur.fetchall()

    cur.execute('select c_id, c_name, c_is_men, c_is_woman from category')
    categories = cur.fetchall()
    for brand in brands:
        cur.execute(f'select * from product where b_id = {brand["b_id"]} and m_id = 1')
        tmp = cur.fetchall()
        exist_products = {}
        for exist_product in tmp:
            exist_products[exist_product['p_url']] = {'p_id': exist_product['p_id'], 'p_count': exist_product['p_count']}

        for category in categories:

            for gender in ('men', 'woman'):
                items = {}
                
                if(category['c_is_'+gender] == 0):
                    continue
                
                driver.get(f'https://kream.co.kr/brands/{brand["b_name"]}?gender={gender}&shop_category_id={category["c_id"]}&sort=popular_score')
                file.write(f'bot1 get_url :  https://kream.co.kr/brands/{brand["b_name"]}?gender={gender}&shop_category_id={category["c_id"]}&sort=popular_score\n')
                time.sleep(1)

                last_height = driver.execute_script("return document.body.scrollHeight")
                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    time.sleep(2)
                    
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        break
                    last_height = new_height
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                driver_items = soup.select('.search_result_list > .search_result_item')

                file.write(f'search products : {len(driver_items)}\n')
                
                for driver_item in driver_items:
                    item_name = driver_item.select_one('.product_info_product_name > .name').text
                    items[item_name] = {}
                    items[item_name]['name'] = item_name
                    items[item_name]['market_id'] = 1
                    items[item_name]['brand_id'] = brand["b_id"]
                    items[item_name]['kr_name'] = driver_item.select_one('.product_info_product_name > .translated_name').text
                    items[item_name]['price'] = re.sub(r'[,\s원-]','',driver_item.select_one('.price > .amount').text)

                    discount_rate = driver_item.select_one('.price > .amount > .discount_rate')
                    if discount_rate != None:
                        items[item_name]['price'] = items[item_name]['price'].replace(discount_rate.text, '')

                    items[item_name]['price'] = int(items[item_name]['price']) if items[item_name]['price'] != "" else 0

                    items[item_name]['url'] = base_url+driver_item.select_one('.item_inner')['href']
                    items[item_name]['img_url'] = driver_item.select_one('.product_img > img')['src']
                

                try:
                    js_items = driver.execute_script("return window.__NUXT__.state['search-tab']['productFeed']['items']")
                except Exception:
                    file.write(f'bot1 : not found js_items')
                    continue
                

                for js_item in js_items:
                    item_name = js_item['product']['release']['name']
                    items[item_name]['origin_price'] = js_item['product']['release']['original_price']
                    items[item_name]['sales'] = js_item['product']['market']['total_sales']
                    items[item_name]['option'] = ','.join(js_item['product']['options'])
                    items[item_name]['img_url'] = ','.join(js_item['product']['release']['image_urls'])
                    items[item_name]['model_number'] = js_item['product']['release']['style_code']
                    items[item_name]['color'] = js_item['product']['release']['colorway']


                for item in items:
                    tmp = items[item]
                    try:
                        result = exist_products[tmp['url']]
                    except Exception:
                        result = None
                    before_sales = 0
                    
                    sql = "insert into product (m_id, b_id, p_name, p_name_kr, p_price, p_origin_price, p_count, p_option, p_model_number, p_color, p_url, p_img_url) values(%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    # crawling list에 리스트 업하고 product에 데이터를 삽입하는 코드
                    if result == None:
                        cur.execute(sql, (tmp['market_id'], tmp['brand_id'], tmp['name'], tmp['kr_name'], tmp['price'], tmp['origin_price'], tmp['sales'], tmp['option'], tmp['model_number'], tmp['color'], tmp['url'],  tmp['img_url']))
                        cur.execute('select * from product order by p_id desc')
                        item_id = cur.fetchone()['p_id']
                    # product의 count 값이 바뀌었으면 crawling list에 리스트업 아니면 프로덕트 데이터만 변경해주는 코드
                    else:
                        item_id = result['p_id']

                        sql = "update product set p_price = %s, p_count = %s, p_option = %s, p_last_crawling_datetime = %s where p_id = %s"
                        cur.execute(sql, (tmp['price'], tmp['sales'], tmp['option'], datetime.now(), item_id))
                        before_sales = result['p_count']

                    if before_sales != tmp['sales']:
                        if tmp['sales'] == '0': continue
                        cur.execute('insert into crawling_product_list(p_id) values(%s)',(item_id))

                conn.commit()  
            file.write(f'bot1 : {brand} {category} ended : {datetime.now()}\n')
            file.flush()

        cur.execute(f'update brand set b_update_at = "{datetime.now()}" where b_id = "{brand["b_id"]}"')
        conn.commit()

except Exception:
    err = traceback.format_exc()
    file.write(f'error bot1 : {err}\n')


file.write(f'end bot1 at : {datetime.now()}\n\n')
file.close()

driver.quit()
conn.close()

