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
def fetch_bunjang_products(cur, last_crawled_p_id, p_count=1, limit=400):
    cur.execute(f"SELECT * FROM bunjang_product WHERE m_id = 6 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

def fetch_category(cur):
    cur.execute('select * from category where m_id = 6')
    tmp_categories = cur.fetchall()
    categories = {}
    for category in tmp_categories:
        categories[category['c_name'].replace(' ', '')] = category['c_id']
    return categories


def update_used_product(cur, product, is_selled):
    cur.execute('update used_product set b_id=%s, p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s', (product['b_id'], 0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into used_product_sell_history(`p_id`, `g_id`, `psh_selled_datetime`, `psh_price`) values(%s, %s, %s, %s)', (product['p_id'], product['g_id'], datetime.now(), product['p_price']))


def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        categories = fetch_category(cur)

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

                data = json.loads(response.content)[data]

                for item in data:
                    crawled_list.append({
                        'title':item['productTitle'], 
                        'brand':product['b_id'],
                        'price':item['productPrice'], 
                        'image':item['productImage'], 
                        'grade':item['productConditionDesc'],
                        'url':'https://m.bunjang.co.kr/products/'+item['p_id'], 
                        'createdAt':item['productCreatedAt'], 
                        'updatedAt':item['productUpdatedAt'],
                        'crawledAt':datetime.now()
                        })
                    

                break

            if rq_status:
                break


            break


    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()