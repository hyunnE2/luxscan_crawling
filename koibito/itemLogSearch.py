import time
import traceback
import pymysql
import re

import requests
from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'koibito/'

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
    cur.execute("SELECT * FROM config WHERE cfg_key = 'koibito_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('koibito_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM product WHERE m_id = 3 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()


def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 3')
    tmp_brands = cur.fetchall()
    
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']
    return brands


def product_update(cur, product, is_selled):
    cur.execute('update product set p_is_possible_crawling=%s, p_price=%s, p_img_url=%s, p_last_crawling_datetime=%s where p_id=%s', (0 if is_selled else 1, product['p_price'], product['p_img_url'], datetime.now(), product['p_id']))
    if is_selled:
        cur.execute('insert into product_sell_history(`p_id`, `g_id`, `psh_datetime`, `psh_price`) values(%s, %s, %s, %s)', (product['p_id'], product['g_id'], datetime.now(), product['p_price']))


def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)
        
        brands = fetch_brand(cur)


        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id, p_count=0)

        if len(products) < 1:
            cur.execute("update config set cfg_value = 0 where cfg_key = 'koibito_crawled_p_id'")
            conn.commit()

        for product in products:
            response = requests.get(product['p_url'])
            if response.status_code != 200:
                write_log(LOG_FILE, f"break : status code is {response.status_code}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            imgs = soup.select('center> table:nth-child(7) > form > tr > td > table > tr > td > div > table > tr > td:nth-child(1) > table > tr:nth-child(2) img')
            product['img_urls'] = ','.join([img['src'] for img in imgs])

            brand = re.sub(r'[,\s]', '', soup.select(".detail_info_list > .info_list_basic > dd")[0].text.strip())
            brand = brand[:brand.find('(')]
            product['b_id'] = 0
            if brands.get(brand) != None:
                product['b_id'] = brands[brand]

            is_sold_out = soup.select_one(".detail_info_title > .infor_price").text
            if is_sold_out.find('품절') > -1:
                product_update(cur, product, True)
                write_log(LOG_FILE, f"sold out p_id : {product['p_id']}")
            else:
                product_update(cur, product, False)
                write_log(LOG_FILE, f"exists p_id : {product['p_id']}")
            cur.execute("update config set cfg_value = %s where cfg_key = 'koibito_crawled_p_id'", (product['p_id']))
            conn.commit()


    except Exception:
        err = traceback.format_exc()
        write_log(LOG_FILE, f"Error: {err}")
    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()