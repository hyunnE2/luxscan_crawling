import requests
from bs4 import BeautifulSoup
import re
import pymysql
from datetime import datetime
from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('KOIBITO_URL')
DB_CONFIG = {
    'host': os.environ.get('HOST'),
    'user': os.environ.get('DB_USER'),
    'password': os.environ.get('DB_PASSWORD'),
    'db': os.environ.get('DB_TABLE'),
    'charset': os.environ.get('CHARSET')
}

SAVE_PATH = os.environ.get('SAVE_PATH')+'koibito/'

LOG_FILE = SAVE_PATH+'itemSearch.log'

# Initialize log file
def init_log(file_path):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(f'start at : {datetime.now()}\n')

# Write log
def write_log(file_path, message):
    with open(file_path, 'a', encoding='euc-kr') as f:
        f.write(message + '\n')

def fetch_grade(cur):
    cur.execute('select * from grade where m_id = 3')
    return cur.fetchall()

try:
    conn = pymysql.connect(**DB_CONFIG)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    init_log(LOG_FILE)

    tmp_grades = fetch_grade(cur)
    grades = {}
    for grade in tmp_grades:
        grades[grade['g_market_grade']] = grade['g_id']

    url = f'{base_url}/update_goods.html'
    i = 1
    while True:
        response = requests.get(url+'?page='+str(i))
        if response.status_code != 200:
            write_log(LOG_FILE, f"break : status code is {response.status_code}")
            break

        soup = BeautifulSoup(response.content, 'html.parser')
        products = soup.select('#product_list > ul > li')

        if len(products) < 1:
            if i == 1:
                write_log(LOG_FILE, f'not found products')
            break
        else:
            write_log(LOG_FILE, f"loaded product count : {len(products)}")
            
        for product in products:
            tables = product.select('table')
            p_url = product.select_one('a')['href']
            name = re.sub(r'[,\s원-]', '', tables[0].text.strip())
            tds = tables[1].select('td')
            
            grade = re.sub(r'[\s]', '', tds[0].text.strip())

            g_id = grades.get(grade)
            price = re.sub(r'[,\s원-]', '', tds[1].text.strip())

            if price.find('거래진행중') > -1:
                price = -1
                write_log(LOG_FILE, f"inserst product")

            sql = """
            INSERT INTO product (m_id, g_id, p_name_kr, p_price, p_url, p_origin_price, p_count, p_model_number, p_color, p_img_url, p_last_crawling_datetime)
            VALUES (3, %s, %s, %s, %s, 0, 1, 0, '', '', NOW())
            ON DUPLICATE KEY UPDATE p_last_crawling_datetime = NOW();
            """
            cur.execute(sql, (g_id, name, price, base_url+'/'+p_url))
            conn.commit()
        i += 1    
        

except Exception as e:
    write_log(LOG_FILE, f"Error: {e}")
finally:
    conn.close()
    write_log(LOG_FILE, f"End at: {datetime.now()}")