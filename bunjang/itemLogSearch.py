import time
import traceback
import pymysql

import requests
from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os
import json

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'bunjang/'

exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

LOG_FILE = SAVE_PATH+'itemLogSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'bunjang_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('bunjang_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_bunjang_products(cur, last_crawled_p_id, p_count=1, limit=100):
    cur.execute(f"SELECT * FROM bunjang_product WHERE m_id = 6 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

def fetch_category(cur):
    cur.execute('select * from category where m_id = 6')
    tmp_categories = cur.fetchall()
    categories = {}
    for category in tmp_categories:
        categories[category['c_name']] = category['c_id']
    return categories


def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 6')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']
    
    return grades


def update_used_product(cur, product, is_selled):
    cur.execute('update used_product set b_id=%s, p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s', (product['b_id'], 0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into used_product_sell_history(`p_id`, `g_id`, `psh_sold_datetime`, `psh_price`) values(%s, %s, %s, %s)', (product['p_id'], product['g_id'], datetime.now(), product['p_price']))


def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        categories = fetch_category(cur)
        grades = fetch_grade(cur)

        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_bunjang_products(cur, last_crawled_p_id, p_count=0)

        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'bunjang_crawled_p_id'")
            write_log(LOG_FILE, 'not found products')
            conn.commit()

        for product in products:
            rq_status = False

            m_id = product['p_url'].split('/')[-1]
            response = requests.get(f'https://api.bunjang.co.kr/api/catalog/v1/products?modelId={m_id}&size=20')

            if response.status_code != 200:
                write_log(LOG_FILE, f"break : status code is {response.status_code}")
                break
            data = json.loads(response.content)
            
            total_pages = data['totalPages']
            total_elements = data['totalElements']

            crawled_list = []
            for i in range(total_pages):
                response = requests.get(f'https://api.bunjang.co.kr/api/catalog/v1/products?modelId={m_id}&page={i}&quickDelivery=false&size=20&sort=date&status=SELLING&status=RESERVED')

                if response.status_code != 200:
                    write_log(LOG_FILE, f"break : status code is {response.status_code}")
                    rq_status = True
                    break

                data = json.loads(response.content)['data']

                for item in data:
                    parent_c_id = None
                    brows_cates = item['categoryName'].split('>')
                    grade = item['productConditionDesc'].strip()

                    if grades.get(grade) == None:
                        cur.execute('insert into `grade`(`m_id`, `g_market_grade`) values(6, %s)', (grade))
                        cur.execute('select * from `grade` where `g_market_grade` = %s', (grade))
                        grades[grade] = cur.fetchone()['g_id']
                        

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
                            
                            conn.commit()

                        parent_c_id = cate

                    crawled_list.append((
                        6,#m_id
                        cate, #c_id
                        product['b_id'], #b_id
                        grades[grade], #g_id
                        item['productTitle'], #p_name_kr
                        item['productPrice'], #p_price
                        'https://m.bunjang.co.kr/products/'+str(item['pid']), #p_url
                        item['productImage'], #p_img_url
                        item['productCreatedAt'], #p_created_datetime
                        item['productUpdatedAt'], #p_created_datetime
                        datetime.now() #p_last_crawling_datetime
                    ))
                
                for crawled_data in crawled_list:
                    cur.execute('insert into used_product(`m_id`,`c_id`,`b_id`,`g_id`,`p_name_kr`,`p_price`,`p_url`,`p_img_url`,`p_created_datetime`,`p_updated_datetime`,`p_last_crawling_datetime`) values(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();', crawled_data)

            if rq_status:
                break



    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error Location : page:{i+1}, modelId:{m_id}")
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()