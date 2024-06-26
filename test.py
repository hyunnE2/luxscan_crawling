import time
import traceback
import pymysql
import re

from selenium import webdriver
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
from datetime import datetime

from dotenv import load_dotenv
import os

load_dotenv()

base_url = os.environ.get('BASE_URL')
host = os.environ.get('HOST')
user = os.environ.get('USER')
password = os.environ.get('PASSWORD')
db = os.environ.get('DB')
charset = os.environ.get('CHARSET')

file = open('crawling_log.txt', 'a', encoding='euc-kr')
file.write(f'start bot1 at : {datetime.now()}\n')

conn = pymysql.connect(host=host, user=user, password=password, db=db, charset=charset)
cur = conn.cursor()

## login 
chrome_options = webdriver.ChromeOptions()
chrome_options.add_argument('--headless')
chrome_options.add_argument('--disable-dev-shm-usage')
browser = webdriver.Chrome()


file.write(f'end bot1 at : {datetime.now()}\n\n')
file.close()

browser.quit()
conn.close()

