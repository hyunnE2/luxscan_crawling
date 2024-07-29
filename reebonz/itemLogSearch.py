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
    print(message)

def get_last_crawled_p_id(cur):
    cur.execute("SELECT * FROM config WHERE cfg_key = 'koibito_crawled_p_id'")
    result = cur.fetchone()
    if result is None:
        # cur.execute("INSERT INTO config(cfg_key, cfg_value) VALUES('koibito_crawled_p_id', 0)")
        return 0
    return int(result['cfg_value'])

# Fetch products to crawl
def fetch_products(cur, last_crawled_p_id, p_count=80, limit=400):
    cur.execute(f"SELECT * FROM product WHERE m_id = 5 AND p_id > {last_crawled_p_id} AND p_count >= {p_count} LIMIT {limit}")
    return cur.fetchall()

def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 5')
    tmp_grades = cur.fetchall()

    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    return grades

def fetch_brand(cur):
    cur.execute('select * from brand where m_id = 5')
    tmp_brands = cur.fetchall()
    brands = {}
    for brand in tmp_brands:
        brands[brand['b_name'].replace(' ', '')] = brand['b_id']

    return brands

def __main__():
    try:
        init_log(LOG_FILE)

        conn = pymysql.connect(**DB_CONFIG)
        cur = conn.cursor(pymysql.cursors.DictCursor)

        
        grades = fetch_grade(cur)
        brands = fetch_brand(cur)

        last_crawled_p_id = get_last_crawled_p_id(cur)
        products = fetch_products(cur, last_crawled_p_id, p_count=0)
        for product in products:
            response = requests.get(product['p_url'])
            print(product['p_url'])
            if response.status_code != 200:
                write_log(LOG_FILE, f"break : status code is {response.status_code}")
                break

            soup = BeautifulSoup(response.content, 'html.parser')
            imgs = soup.select('center> table:nth-child(7) > form > tr > td > table > tr > td > div > table > tr > td:nth-child(1) > table > tr:nth-child(2) img')
            img_urls = ','.join([img['src'] for img in imgs])

            brand = re.sub(r'[,\s]', '', soup.select(".detail_info_list > .info_list_basic > dd")[0].text.strip())
            brand = brand[:brand.find('(')]
            b_id = 0
            if brands.get(brand) != None:
                b_id = brands[brand]

            is_sold_out = soup.select_one(".button.orange.order")
            if is_sold_out == None:
                write_log(LOG_FILE, f"sold out p_id : {product['p_id']}")
            else:
                cur.execute(f"update product set b_id = {b_id}, p_img_url='{img_urls}' where p_id = {product['p_id']}")
                write_log(LOG_FILE, f"exists p_id : {product['p_id']}")
            break


    except Exception:
        err = traceback.format_exc()
        print(err)

    finally:
        conn.close()
        write_log(LOG_FILE, f"End at: {datetime.now()}")

if __name__ == "__main__":
    __main__()