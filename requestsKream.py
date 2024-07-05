import time
import requests
import json
from openpyxl import Workbook, load_workbook

import pymysql
import pymysql.cursors
import traceback

import pandas as pd

from datetime import datetime
from py_mini_racer import py_mini_racer

from dotenv import load_dotenv
import os

from fake_useragent import UserAgent

ua = UserAgent()
ua.browsers.remove('chrome')

load_dotenv()

base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
db = os.environ.get('DB_TABLE')
charset = os.environ.get('CHARSET')


file = open('crawling(bot_3).log', 'a', encoding='euc-kr')
file.write(f'start bot3 at : {datetime.now()}\n')

session = requests.Session()

try:
    conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
    cur = conn.cursor(pymysql.cursors.DictCursor)
    cur.execute('select * from product')
    products = cur.fetchall()

    file.write(f'bot3 : loaded products {len(products)}\n')

    i = 0
    for product in products:
        if i % 400 == 0:
            headers = {
                'user-agent' : ua.random,
            }
            print('change user-agent')
            
            response = session.get(product['p_url'], headers=headers)
            for j in range(0, 5):
                headers = {
                    'user-agent' : ua.random,
                }
                response = session.get(product['p_url'], headers=headers)

                if response.status_code == 200:
                    break
        else:
            response = session.get(product['p_url'], headers=headers)

        html_content = response.text
        
        if response.status_code == 200:
            script_start = html_content.find("window.__NUXT__=")
            script_end = html_content.find("</script>", script_start)
            if script_start == -1 or script_end == -1:
                file.write("script not found\n")
            else:
                script_content = html_content[script_start:script_end]
                
                ctx = py_mini_racer.MiniRacer()

                ctx.eval("window={};")

                ctx.eval(script_content)

                nuxt_data = ctx.eval("JSON.stringify(window.__NUXT__.state.product.response.sales_options)")
                if nuxt_data == None:
                    nuxt_data = ctx.eval("JSON.stringify(window.__NUXT__.state.product.response.sale_info.details.options)")

                    for item in json.loads(nuxt_data):
                        if item['is_show_option_price'] == False: continue

                        if item['price'] != None:
                            price = item['price']
                        else:
                            price = 0
                        fast_price = 0
                        cur.execute(f"insert into price_by_option_of_product(`p_id`, `pboop_option`, `pboop_price`, `pboop_quick_price`) values ({product['p_id']},'{item['key']}',{price},{fast_price}) on DUPLICATE KEY UPDATE `pboop_price` = {price}, `pboop_quick_price` = {fast_price}, `pboop_datetime` = '{datetime.now()}'")          
                else:    
                    for item in json.loads(nuxt_data):
                        if item['lowest_normal'] != None:
                            price = item['lowest_normal']
                        else:
                            price = 0

                        if item['lowest_100'] != None:
                            fast_price = item['lowest_100']
                        else:
                            fast_price = 0
                        cur.execute(f"insert into price_by_option_of_product(`p_id`, `pboop_option`, `pboop_price`, `pboop_quick_price`) values ({product['p_id']},'{item['option']}',{price},{fast_price}) on DUPLICATE KEY UPDATE `pboop_price` = {price}, `pboop_quick_price` = {fast_price}, `pboop_datetime` = '{datetime.now()}'")          
            print(f"success. p_id : {product['p_id']}")
            file.write(f"sucess. p_id : {product['p_id']}\n")     
        else:
            print(f"Failed to retrieve the web page status={response.status_code}. p_id : {product['p_id']}\n")
            file.write(f"Failed to retrieve the web page status={response.status_code}. p_id : {product['p_id']}\n")
            break

        file.write(f'p_id : {product["p_id"]} end at :{datetime.now()}\n')
        file.flush()

        conn.commit()

        i += 1

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
    

    if not os.path.exists('kream_test_data.xlsx'):
        wb = Workbook()
        ws = wb.active
        ws.title = "result_sheet"

        wb.save('kream_test_data.xlsx')


    with pd.ExcelWriter('kream_test_data.xlsx', engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
        file.write('writing\n')
        pd.DataFrame(result).to_excel(writer, sheet_name='result_sheet', index=False)

except Exception:
    err = traceback.format_exc()
    file.write(f'error bot3 : {err}\n')

file.write(f'ended bot3 at : {datetime.now()}\n')

conn.close()
file.close()
