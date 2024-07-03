import requests
import json

import pymysql
import pymysql.cursors
import traceback

import pandas as pd

from datetime import datetime
from py_mini_racer import py_mini_racer

from dotenv import load_dotenv
import os

load_dotenv()


base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
db = os.environ.get('DB_TABLE')
charset = os.environ.get('CHARSET')


file = open('crawling.log', 'a', encoding='euc-kr')
file.write(f'start bot3 at : {datetime.now()}\n')


session = requests.Session()

headers = {
    'user-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Whale/3.26.244.21 Safari/537.36',
}

print('start at :', datetime.now())

try:
    conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute('select * from product')
    products = cur.fetchall()

    for product in products:
        response = session.get(product['p_url'], headers=headers)
        html_content = response.text
        
        if response.status_code == 200:
            script_start = html_content.find("window.__NUXT__=")
            script_end = html_content.find("</script>", script_start)
            
            if script_start == -1 or script_end == -1:
                print("script not found")
            else:
                script_content = html_content[script_start:script_end]

                ctx = py_mini_racer.MiniRacer()

                ctx.eval("window={};")

                ctx.eval(script_content)

                nuxt_data = ctx.eval("JSON.stringify(window.__NUXT__.state.product.response.sales_options)")

                for item in json.loads(nuxt_data):
                    if item['lowest_normal'] != None:
                        price = item['lowest_normal']
                    else:
                        price = 0

                    if item['lowest_100'] != None:
                        fast_price = item['lowest_100']
                    else:
                        fast_price = 0
                    cur.execute(f"insert into price_by_option_of_product(`p_id`, `pboop_option`, `pboop_price`, `pboop_quick_price`) values ({product['p_id']},'{item["option"]}',{price},{fast_price}) on DUPLICATE KEY UPDATE `pboop_price` = {price}, `pboop_quick_price` = {fast_price}, `pboop_datetime` = '{datetime.now()}'")          
                    
        else:
            print(f"Failed to retrieve the web page. Status code: {response.status_code}")
        print('end at :', datetime.now())

        conn.commit()

    cur.execute('select p_name, p_url, pboop_option, pboop_price, pboop_quick_price, pboop_datetime from price_by_option_of_product join product on price_by_option_of_product.p_id = product.p_id')
    rows = cur.fetchall()
    
    result = {'name':[],'url':[],'option':[],'price':[],'quick_price':[],'datetime':[]}

    for row in rows:
        result['name'].append(row['p_name'])
        result['url'].append(row['p_url'])
        result['option'].append(row['pboop_option'])
        result['price'].append(row['pboop_price'])
        result['quick_price'].append(row['pboop_quick_price'])
        result['datetime'].append(row['pboop_datetime'])
    
    with pd.ExcelWriter('kream_test_data.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        print('writing')
        pd.DataFrame(result).to_excel(writer, sheet_name='result_sheet', index=False)

except Exception:
    err = traceback.format_exc()
    file.write(f'error bot3 : {err}\n')

file.write(f'ended bot3 at : {datetime.now()}\n')

conn.close()
file.close()
