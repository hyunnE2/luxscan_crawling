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

base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
db = os.environ.get('DB_TABLE')
charset = os.environ.get('CHARSET')

file = open('crawling(bot_1).log', 'a', encoding='euc-kr')
file.write(f'start bot1 at : {datetime.now()}\n')

conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
cur = conn.cursor()

## login 
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

driver = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
driver.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
driver.execute_cdp_cmd('Network.enable', {})

try:
    cur.execute('select b_id, b_name from brand where b_name = "Nike"')
    brands = cur.fetchall()

    cur.execute('select c_id, c_name, c_is_men, c_is_woman as c from category limit 1')
    categories = cur.fetchall()

    for brand in brands:
        for category in categories:

            for i in range(2):
                items = {}

                if(category[i+2] == 0):
                    continue
                gender = 'men' if i == 0 else 'woman'
                driver.get(f'https://kream.co.kr/brands/{brand[1]}?tab=44&gender={gender}&shop_category_id={category[0]}&sort=popular_score')
                file.write(f'bot1 get_url :  https://kream.co.kr/brands/{brand[1]}?tab=44&gender={gender}&shop_category_id={category[0]}&sort=popular_score\n')
                time.sleep(1)

                print('enter while')
                last_height = driver.execute_script("return document.body.scrollHeight")
                while True:
                    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                    
                    time.sleep(1)
                    
                    new_height = driver.execute_script("return document.body.scrollHeight")
                    
                    if new_height == last_height:
                        break
                    print(last_height, new_height)
                    last_height = new_height
                print('quit while')
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')

                driver_items = soup.select('.search_result_list > .search_result_item')

                for driver_item in driver_items:
                    item_name = driver_item.select_one('.product_info_product_name > .name').text
                    items[item_name] = {}
                    items[item_name]['name'] = item_name
                    items[item_name]['market_id'] = 1
                    items[item_name]['brand_id'] = brand[0]
                    items[item_name]['kr_name'] = driver_item.select_one('.product_info_product_name > .translated_name').text
                    items[item_name]['price'] = re.sub(r'[,\s원-]','',driver_item.select_one('.price > .amount').text)

                    discount_rate = driver_item.select_one('.price > .amount > .discount_rate')
                    if discount_rate != None:
                        items[item_name]['price'] = items[item_name]['price'].replace(discount_rate.text, '')

                    items[item_name]['price'] = int(items[item_name]['price']) if items[item_name]['price'] != "" else 0

                    items[item_name]['url'] = base_url+driver_item.select_one('.item_inner')['href']
                    items[item_name]['img_url'] = driver_item.select_one('.product_img > img')['src']
                
                js_items = driver.execute_script("return window.__NUXT__.state['search-tab']['productFeed']['items']")
                
                for js_item in js_items:
                    item_name = js_item['product']['release']['name']
                    items[item_name]['sales'] = js_item['product']['market']['total_sales']
                    items[item_name]['option'] = ','.join(js_item['product']['options'])

                
                for item in items:
                    tmp = items[item]
                    cur.execute(f'select * from product where p_url = "{tmp["url"]}"')
                    result = cur.fetchall()
                    before_sales = 0
                    
                    sql = "insert into product (m_id, b_id, p_name, p_name_kr, p_price, p_count, p_option, p_url, p_img_url) values(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
                    # crawling list에 리스트 업하고 product에 데이터를 삽입하는 코드
                    if len(result) < 1:
                        cur.execute(sql, (tmp['market_id'], tmp['brand_id'], tmp['name'], tmp['kr_name'], tmp['price'], tmp['sales'], tmp['option'], tmp['url'],  tmp['img_url']))
                        cur.execute('select * from product order by p_id desc')
                        item_id = cur.fetchone()[0]
                    # product의 count 값이 바뀌었으면 crawling list에 리스트업 아니면 프로덕트 데이터만 변경해주는 코드
                    else:
                        item_id = result[0][0]

                        sql = "update product set p_price = %s, p_count = %s, p_option = %s, p_last_crawling_datetime = %s where p_id = %s"
                        cur.execute(sql, (tmp['price'], tmp['sales'], tmp['option'], datetime.now(), item_id))
                        before_sales = result[0][6]

                    if before_sales != tmp['sales']:
                        cur.execute('insert into crawling_product_list(p_id) values(%s)',(item_id))


                conn.commit()  
            file.write(f'bot1 : {brand} {category} ended : {datetime.now()}\n')
            file.flush()

        cur.execute(f'update brand set b_update_at = "{datetime.now()}" where b_id = "{brand[0]}"')
        conn.commit()

except Exception:
    err = traceback.format_exc()
    file.write(f'error bot1 : {err}\n')


file.write(f'end bot1 at : {datetime.now()}\n\n')
file.close()

driver.close()
conn.close()

