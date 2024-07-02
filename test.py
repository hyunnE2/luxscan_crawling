import time

import pandas as pd

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
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



## login 
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


file_name = 'kream_test_data.xlsx'
df = pd.read_excel(file_name, sheet_name='refer_sheet', header=None, engine='openpyxl').fillna('__NOT_DATA__')

result_frame = {'참고 열': [], '사이즈': [], '현재 빠른 배송': [], '일반 배송': [], '최신 수집일': []}

for r_index in range(0, len(df.index)):
    refer_col = 'A'+str(r_index+1)
    print(len(df.index), '/',(r_index+1))
    if r_index % 2000 == 0: 
        browser.get(base_url+'/login')
        time.sleep(2)
        id = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[1]/div/input')
        id.send_keys(crawling_id)

        pw = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[2]/div/input')
        pw.send_keys(crawling_pw)

        browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[3]').click()

        time.sleep(2)
    if df.loc[r_index].values[0] != '__NOT_DATA__':
        browser.get(df.loc[r_index].values[0])
        time.sleep(0.6)

        # print(browser.find_element(By.CSS_SELECTOR, '.btn_wrap > .division_btn_box > button:nth-child(2)').get_attribute('outerHTML'))
        browser.find_element(By.CSS_SELECTOR, '.btn_wrap > .division_btn_box > button:nth-child(2)').click()

        try:
            selec_items = WebDriverWait(browser, 10).until(
                EC.presence_of_all_elements_located((By.CSS_SELECTOR, '.select_list > .select_item'))
            )
        except Exception as e:
            print(f"Failed to find elements: {e}")
            browser.quit()
        for item in selec_items:
            price = '0'
            fast_price = '0'

            item.find_element(By.CSS_SELECTOR, '.buy').click()
            
            soup = BeautifulSoup(browser.page_source, 'html.parser')
            btns = soup.select('.order_btn_area > .clickable')

            for btn_idx in range(0, 2):
                tmp = btns[btn_idx].select_one('.order_price').text
                if len(btns) == 1: 
                    price = tmp
                    break
                else:
                    if btn_idx == 0:
                        fast_price = tmp
                    else:
                        price = tmp
            
            result_frame['참고 열'].append(refer_col)
            result_frame['사이즈'].append(item.find_element(By.CSS_SELECTOR, '.size').text)
            result_frame['최신 수집일'].append(datetime.now())
            result_frame['일반 배송'].append(price)
            result_frame['현재 빠른 배송'].append(fast_price)

with pd.ExcelWriter(file_name, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    print('writing')
    pd.DataFrame(result_frame).to_excel(writer, sheet_name='result_sheet', index=False)
    
    

browser.close()