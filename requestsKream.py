import requests
import json
import time
import datetime

from selenium import webdriver
import pandas as pd
from selenium.webdriver.common.by import By
from py_mini_racer import py_mini_racer


LOGIN_URL = 'https://kream.co.kr/login'
USERNAME = 'youloveamazon@gmail.com'
PASSWORD = 'Hopaes001$$'


session = requests.Session()

chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument("--headless=new")
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--window-size=1920x1080")
chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36")


browser = webdriver.Chrome('C:/Users/leedo/Downloads/chromedriver-win64/chromedriver-win64/chromedriver.exe', options=chrome_options)

browser.get(LOGIN_URL)
time.sleep(2)
id = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[1]/div/input')
id.send_keys(USERNAME)

pw = browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[2]/div/input')
pw.send_keys(PASSWORD)

browser.find_element(By.XPATH, '//*[@id="wrap"]/div[3]/div/div/div[3]').click()

time.sleep(2)

for cookie in browser.get_cookies():
    c = {cookie['name'] : cookie['value']}
    session.cookies.update(c)

browser.close()


headers = {
    'user-agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Whale/3.26.244.21 Safari/537.36',
}

print('start at : ', datetime.datetime.now())

file_name = 'kream_test_data.xlsx'
df = pd.read_excel(file_name, sheet_name='refer_sheet', header=None, engine='openpyxl').fillna('__NOT_DATA__')

result_frame = {'참고 열': [], '사이즈': [], '현재 빠른 배송': [], '일반 배송': [], '최신 수집일': []}
for r_index in range(0, len(df.index)):
    refer_col = 'A'+str(r_index+1)
    print(len(df.index), '/',(r_index+1))

    if df.loc[r_index].values[0] != '__NOT_DATA__':
        response = session.get(df.loc[r_index].values[0], headers=headers)
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
                    if 'lowest_normal' in item['product_option']:
                        fast_price = item['product_option']['lowest_normal']
                    else:
                        fast_price = '0'

                    if 'lowest_100' in item['product_option']:
                        price = item['product_option']['lowest_100']
                    else:
                        price = '0'

                    result_frame['참고 열'].append(refer_col)
                    result_frame['사이즈'].append(item['option'])
                    result_frame['일반 배송'].append(price)
                    result_frame['현재 빠른 배송'].append(fast_price)
                    result_frame['최신 수집일'].append(datetime.datetime.now())
        else:
            print(f"Failed to retrieve the web page. Status code: {response.status_code}")
            
        print('end at : ', datetime.datetime.now())
    else:
        print('__NOT_FOUND__')

print(result_frame)

with pd.ExcelWriter(file_name, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
    print('writing')
    pd.DataFrame(result_frame).to_excel(writer, sheet_name='result_sheet', index=False)
