import time
import re
import pymysql
import pymysql.cursors
import traceback

from selenium import webdriver
from selenium.webdriver.common.by import By
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


crawling_id = os.environ.get('CRAWLING_ID')
crawling_pw = os.environ.get('CRAWLING_PW')

file = open('crawling(bot_2).log', 'a', encoding='euc-kr')
file.write(f'start bot2 at : {datetime.now()}\n')

# setting chrome options
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


exe_chromedriver_path = os.environ.get('EXECUTABLE_CHROMEDRIVER_PATH')

browser = webdriver.Chrome(executable_path=exe_chromedriver_path, options=chrome_options)
browser.execute_cdp_cmd('Network.setUserAgentOverride', {"userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'})
browser.execute_cdp_cmd('Network.enable', {})


try:
    conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
    cur = conn.cursor(pymysql.cursors.DictCursor)

    cur.execute('SET SESSION sql_mode=(SELECT REPLACE(@@sql_mode,\'ONLY_FULL_GROUP_BY\',\'\'))')

    cur.execute('select product.p_id as p_id, cpl_id, p_url from crawling_product_list join product on crawling_product_list.p_id = product.p_id order by cpl_id asc limit 1000')
    crawling_items = cur.fetchall()
    
    
    if len(crawling_items) > 0:
        file.write(f'bot2 : delete {crawling_items[0]["cpl_id"]} ~ {crawling_items[-1]["cpl_id"]}\n')
        cur.execute(f'delete from crawling_product_list where cpl_id >= {crawling_items[0]["cpl_id"]} and cpl_id <= {crawling_items[-1]["cpl_id"]}')
        if len(crawling_items) < 999:
            cur.execute(f'truncate crawling_product_list')    
    else:
        file.write(f'bot2 : truncated\n')
        cur.execute(f'truncate crawling_product_list')
    # if len(crawling_items) < 1000:
    #     cur.execute('truncate crawling_product_list')
    # else:
    #     cur.execute(f'delete from crawling_product_list where cpl_id >= {crawling_items[0]['cpl_id']} and cpl_id <= {crawling_items[-1]['cpl_id']}')

    ## login 
    browser.get(base_url+'/login')
    time.sleep(2)
    id = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[1]/div/input')
    id.send_keys(crawling_id)

    pw = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[2]/div/input')
    pw.send_keys(crawling_pw)

    browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[3]').click()

    time.sleep(2)

    for crawling_item in crawling_items:
        count = 0

        sql = 'insert into product_sell_history(p_id, psh_option, psh_price, psh_is_quickly, psh_datetime) values'

        file.write(f'bot2 crawling url : {crawling_item["p_url"]}\n')

        browser.get(crawling_item['p_url'])
        time.sleep(2)

        browser.find_element(By.CSS_SELECTOR, '.tab_content > .outlinegrey').click()        

        cur.execute(f'select count(*) as count, date(psh_datetime) as psh_datetime from product_sell_history where p_id = {crawling_item["p_id"]} group by psh_datetime order by psh_datetime desc')
        last_data = cur.fetchone()
        if last_data == None:
            last_data = {}
            last_data['psh_datetime'] = datetime.strptime('2000-01-01', '%Y-%m-%d')
            count = 0
        else:
            last_data['psh_datetime'] = datetime.strptime(str(last_data['psh_datetime']), '%Y-%m-%d')
            count = int(last_data['count'])
        
        scrollItem = browser.find_element(By.CSS_SELECTOR, '.market_price_table > .price_body')
        
        tmp = -1
        scrollY = 0
        while tmp != scrollY:
            isbreak = False

            scrollY += 8000
            tmp = browser.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)
            
            time.sleep(0.6)

            scrollY += 8000
            scrollY = browser.execute_script(f'arguments[0].scrollTo(0, {scrollY}); return arguments[0].scrollHeight', scrollItem)

            soup = BeautifulSoup(browser.page_source, 'html.parser')
            browser_items = soup.select('.price_body > .body_list > .list_txt:nth-child(3) > span')

            for i in browser_items:
                date = datetime.strptime('20' + i.text.replace('/', '-'), '%Y-%m-%d')
                
                
                if date > last_data['psh_datetime']:
                    isbreak = True
                    break

            if isbreak:
                break
        
        browser_items = soup.select('.price_body > .body_list')

        insert_items = []
        for item in browser_items:
            txt_list = item.select('.list_txt')
            option = txt_list[0].text
            
            price = re.sub(r'[,\s원-]','',txt_list[1].text)
            price = int(price) if price != "" else 0
            
            date = ('20'+txt_list[2].select('span')[-1].text).replace('/', '-')
            
            quickly = 0 if item.select_one('.express_icon') != None else 1

            insert_items.append({'option':option, 'price':price, 'date':date, 'quickly':quickly})

        sorted_items = sorted(insert_items, key=lambda item: item['date'])
        
        valid_sql = False
        for item in sorted_items:
            date = datetime.strptime(item['date'], '%Y-%m-%d')

            if date < last_data['psh_datetime']: 
                continue
            elif date == last_data['psh_datetime']:
                if count > 0:
                    count -= 1
                    continue
            
            sql += f'({crawling_item["p_id"]}, \"{item["option"]}\", {item["price"]}, {item["quickly"]}, \"{item["date"]}\") ,'
            valid_sql = True
        
        if valid_sql:
            sql = sql[0:-2]
            cur.execute(sql)
            conn.commit()
except Exception:
    err = traceback.format_exc()
    file.write(f'error bot2 : {err}\n')

file.write(f'end bot2 at : {datetime.now()}\n\n')
file.close()

browser.quit()
conn.close()
