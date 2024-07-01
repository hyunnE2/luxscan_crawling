import pandas as pd
import pymysql

from selenium import webdriver
from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os


base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('DB_USER')
password = os.environ.get('DB_PASSWORD')
db = os.environ.get('DB_TABLE')
charset = os.environ.get('CHARSET')

file = open('crawling.log', 'a', encoding='euc-kr')
file.write(f'start bot1 at : {datetime.now()}\n')

conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
cur = conn.cursor()

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
df = pd.read_excel(file_name, sheet_name='TEST_SHEET', header=None).fillna('__NOT_DATA__')

for r_index in range(len(df.index)):
    print(r_index, df.loc[r_index].values[0], df.loc[r_index].values[0] == '__NOT_DATA__')


